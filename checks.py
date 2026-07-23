from __future__ import annotations

import discord
from discord import app_commands

from config import Settings


def member_role_ids(interaction: discord.Interaction) -> set[int]:
    member = interaction.user
    if not isinstance(member, discord.Member):
        return set()
    return {role.id for role in member.roles}


def is_admin(settings: Settings):
    async def predicate(interaction: discord.Interaction) -> bool:
        return bool(member_role_ids(interaction) & settings.admin_role_ids)
    return app_commands.check(predicate)


def is_team_manager(settings: Settings):
    async def predicate(interaction: discord.Interaction) -> bool:
        allowed = settings.admin_role_ids | settings.league_official_role_ids
        return bool(member_role_ids(interaction) & allowed)
    return app_commands.check(predicate)
