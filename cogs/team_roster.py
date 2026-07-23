from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from checks import is_admin, is_team_manager
from config import Settings
from services.sheets import SheetsRepository


class TeamRosterCog(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
        settings: Settings,
        repository: SheetsRepository,
    ):
        self.bot = bot
        self.settings = settings
        self.repo = repository

    team = app_commands.Group(
        name="team",
        description="Manage league teams and rosters.",
    )

    @team.command(name="create", description="Create a new team.")
    @app_commands.describe(
        name="Official team name",
        timezone_name="Team time zone, such as America/Chicago",
        team_role="Discord role associated with this team",
    )
    @is_admin
    async def create_team(
        self,
        interaction: discord.Interaction,
        name: str,
        timezone_name: str,
        team_role: discord.Role,
    ):
        await interaction.response.defer(ephemeral=True)
        try:
            team = self.repo.create_team(
                name=name,
                timezone_name=timezone_name,
                discord_role_id=team_role.id,
                created_by=interaction.user.id,
            )
        except ValueError as exc:
            await interaction.followup.send(str(exc), ephemeral=True)
            return

        await interaction.followup.send(
            f"Created **{team['Team Name']}** with ID `{team['Team ID']}`.",
            ephemeral=True,
        )

    @team.command(name="roster-add", description="Add a player to a team roster.")
    @app_commands.describe(
        team_name="Official team name",
        player="Discord member to roster",
        steam_id="Player Steam ID; use N/A temporarily if unavailable",
    )
    @is_team_manager
    async def roster_add(
        self,
        interaction: discord.Interaction,
        team_name: str,
        player: discord.Member,
        steam_id: str = "N/A",
    ):
        await interaction.response.defer(ephemeral=True)
        team = self.repo.find_team_by_name(team_name)
        if not team:
            await interaction.followup.send("Team not found.", ephemeral=True)
            return
        if team["Status"] != "Active":
            await interaction.followup.send(
                "Players cannot be added to a withdrawn team.",
                ephemeral=True,
            )
            return

        try:
            result = self.repo.add_roster_member(
                team=team,
                discord_user_id=player.id,
                display_name=player.display_name,
                steam_id=steam_id,
                added_by=interaction.user.id,
            )
        except ValueError as exc:
            await interaction.followup.send(str(exc), ephemeral=True)
            return

        await interaction.followup.send(
            f"Added **{result['Display Name']}** to **{team['Team Name']}**.",
            ephemeral=True,
        )

    @team.command(name="roster-remove", description="Remove a player from a roster.")
    @app_commands.describe(
        team_name="Official team name",
        player="Discord member to remove",
    )
    @is_team_manager
    async def roster_remove(
        self,
        interaction: discord.Interaction,
        team_name: str,
        player: discord.Member,
    ):
        await interaction.response.defer(ephemeral=True)
        team = self.repo.find_team_by_name(team_name)
        if not team:
            await interaction.followup.send("Team not found.", ephemeral=True)
            return

        try:
            removed = self.repo.remove_roster_member(team["Team ID"], player.id)
        except ValueError as exc:
            await interaction.followup.send(str(exc), ephemeral=True)
            return

        await interaction.followup.send(
            f"Removed **{removed['Display Name']}** from **{team['Team Name']}**.",
            ephemeral=True,
        )

    @team.command(
        name="rep-add",
        description="Assign a rostered player as a representative.",
    )
    @app_commands.describe(
        team_name="Official team name",
        player="Rostered Discord member",
    )
    @is_team_manager
    async def representative_add(
        self,
        interaction: discord.Interaction,
        team_name: str,
        player: discord.Member,
    ):
        await interaction.response.defer(ephemeral=True)
        team = self.repo.find_team_by_name(team_name)
        if not team:
            await interaction.followup.send("Team not found.", ephemeral=True)
            return

        try:
            member = self.repo.assign_representative(
                team["Team ID"],
                player.id,
                interaction.user.id,
            )
        except ValueError as exc:
            await interaction.followup.send(str(exc), ephemeral=True)
            return

        await interaction.followup.send(
            f"Assigned **{member['Display Name']}** as a representative for "
            f"**{team['Team Name']}**.",
            ephemeral=True,
        )

    @team.command(name="rep-remove", description="Remove representative authority.")
    @app_commands.describe(
        team_name="Official team name",
        player="Current team representative",
    )
    @is_team_manager
    async def representative_remove(
        self,
        interaction: discord.Interaction,
        team_name: str,
        player: discord.Member,
    ):
        await interaction.response.defer(ephemeral=True)
        team = self.repo.find_team_by_name(team_name)
        if not team:
            await interaction.followup.send("Team not found.", ephemeral=True)
            return

        try:
            member = self.repo.remove_representative(team["Team ID"], player.id)
        except ValueError as exc:
            await interaction.followup.send(str(exc), ephemeral=True)
            return

        await interaction.followup.send(
            f"Removed representative authority from **{member['Display Name']}**.",
            ephemeral=True,
        )

    @team.command(name="roster-view", description="View a team's active roster.")
    @app_commands.describe(team_name="Official team name")
    async def roster_view(
        self,
        interaction: discord.Interaction,
        team_name: str,
    ):
        team = self.repo.find_team_by_name(team_name)
        if not team:
            await interaction.response.send_message("Team not found.", ephemeral=True)
            return

        members = self.repo.get_active_roster(team["Team ID"])
        if not members:
            description = "No active roster members."
        else:
            lines = []
            for member in members:
                rep_marker = (
                    " — **Team Representative**"
                    if member["Is Representative"]
                    else ""
                )
                steam = (
                    f" | Steam: `{member['Steam ID']}`"
                    if member["Steam ID"] and member["Steam ID"] != "N/A"
                    else ""
                )
                lines.append(
                    f"<@{member['Discord User ID']}>{rep_marker}{steam}"
                )
            description = "\n".join(lines)

        embed = discord.Embed(
            title=f"{team['Team Name']} Roster",
            description=description,
        )
        embed.add_field(name="Team ID", value=team["Team ID"], inline=True)
        embed.add_field(name="Time Zone", value=team["Time Zone"], inline=True)
        embed.add_field(name="Status", value=team["Status"], inline=True)
        await interaction.response.send_message(embed=embed)


async def setup(
    bot: commands.Bot,
    settings: Settings,
    repository: SheetsRepository,
):
    await bot.add_cog(TeamRosterCog(bot, settings, repository))
