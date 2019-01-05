import datetime
import glob
import logging
import os
import typing
import ujson
from collections import Counter

import discord
import psutil
from aiohttp import ClientSession
from discord import User, Guild
from discord.ext import commands
from discord.ext.commands import Command

from utils.iceteacontext import IceTeaContext


class Iceteabot(commands.Bot):
    def __init__(self, *args, **kwargs):
        self.config: dict = kwargs.pop("config")
        self.name: str = self.config.get("name", "iceteabot")
        self.default_prefix: str = self.config.get("default_prefix", "<<<")
        self.uptime: datetime.datetime = datetime.datetime.utcnow()
        self.command_stats: typing.Dict[Guild, typing.Dict[User, typing.Counter[Command, int]]] = {}
        self.owner: User = None
        self.cog_path: str = "cogs"
        self.aioconnection: ClientSession = ClientSession(json_serialize=ujson.dumps, loop=self.loop)
        self.loop.create_task(self._initialize())
        super(Iceteabot, self).__init__(
            command_prefix=commands.when_mentioned_or(self.default_prefix), activity=discord.Game(self.config['game']),
            *args, **self.config)
        self.remove_command("help")

    def run(self, *args, **kwargs):
        return super(Iceteabot, self).run(self.config['api_keys']['discord'])

    def load_extension(self, name):
        return super(Iceteabot, self).load_extension(f"{self.cog_path}.{name}")

    def unload_extension(self, name):
        return super(Iceteabot, self).unload_extension(f"{self.cog_path}.{name}")

    def get_context(self, message, *, cls=IceTeaContext):
        return super(Iceteabot, self).get_context(message, cls=cls)

    def setup_logging(self):
        logger = logging.getLogger("discord")
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(filename="data/iceteabot.log", encoding='utf-8', mode='w')
        handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
        logger.addHandler(handler)
        error_logger = logging.getLogger("errors")
        error_logger.setLevel(logging.INFO)
        handler = logging.FileHandler(filename="data/error.log", encoding='utf-8', mode='w')
        handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
        error_logger.addHandler(handler)

    async def _initialize(self):
        await self.wait_until_ready()
        application_info = await self.application_info()
        self.owner = application_info.owner
        for guild in self.guilds:
            self.command_stats[guild] = {member: Counter() for member in guild.members if not member.bot}

        startup_extensions = [f"{os.path.basename(ext)[:-3]}"
                              for ext in glob.glob("cogs/*.py")]

        for extension in startup_extensions:
            try:
                self.load_extension(extension)
            except Exception as e:
                exc = '{}: {} on cog: {}'.format(type(e).__name__, e, extension)
                print(exc)

        print(f"Successfully logged in as {self.user}\n" +
              f"Using version {discord.__version__} of discord.py\n" +
              f"Using {psutil.Process().memory_full_info().uss / 1024 ** 2} of ram\n" +
              f"loaded {len(self.extensions)} cogs\n" +
              f"{'-' * 15}")
