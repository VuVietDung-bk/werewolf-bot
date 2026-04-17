from __future__ import annotations

from typing import Optional

import discord
from discord.ext import commands

from games.base_game import BaseGame


class MinigameBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        super().__init__(
            command_prefix="g!",
            intents=intents,
            help_command=None,
        )

        self.current_game: Optional[BaseGame] = None
        self.current_game_type = None

    async def setup_hook(self):
        await self.load_extension("commands.host_commands")
        await self.load_extension("commands.user_commands")
        await self.tree.sync()
        print("Commands synced!")

    async def on_ready(self):
        print(f"{self.user} đã online!")

