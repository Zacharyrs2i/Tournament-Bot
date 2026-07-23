from __future__ import annotations

import logging

import discord
from discord.ext import commands

from cogs.team_roster import setup as setup_team_roster
from config import load_settings
from services.sheets import SheetsRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hll-roster-bot")


class HLLBot(commands.Bot):
    def __init__(self):
        self.settings = load_settings()
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

        self.repository = SheetsRepository(
            sheet_id=self.settings.google_sheet_id,
            service_account_info=self.settings.service_account_info,
        )

    async def setup_hook(self):
        await setup_team_roster(self, self.settings, self.repository)

        if self.settings.test_guild_id:
            guild = discord.Object(id=self.settings.test_guild_id)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            logger.info("Synced %s commands to test guild.", len(synced))
        else:
            synced = await self.tree.sync()
            logger.info("Synced %s global commands.", len(synced))

    async def on_ready(self):
        logger.info(
            "Logged in as %s (%s)",
            self.user,
            self.user.id if self.user else "unknown",
        )


bot = HLLBot()
bot.run(bot.settings.discord_token)
