from __future__ import annotations

import os

import discord
from discord import app_commands


def _role_ids(name: str) -> set[int]:
    raw = os.getenv(name, "")
    return {int(item.strip()) for item in raw.split(",") if item.strip()}


def member_role_ids(interaction: discord.Interaction) -> set[int]:
    member = interaction.user
    if not isinstance(member, discord.Member):
        return set()
    return {role.id for role in member.roles}


def is_admin():
    async def predicate(interaction: discord.Interaction) -> bool:
        return bool(member_role_ids(interaction) & _role_ids("ADMIN_ROLE_IDS"))

    return app_commands.check(predicate)


def is_team_manager():
    async def predicate(interaction: discord.Interaction) -> bool:
        allowed = _role_ids("ADMIN_ROLE_IDS") | _role_ids("LEAGUE_OFFICIAL_ROLE_IDS")
        return bool(member_role_ids(interaction) & allowed)

    return app_commands.check(predicate)
