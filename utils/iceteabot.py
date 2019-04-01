import asyncio
import datetime
import glob
import logging
import os
import traceback
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
from utils.paginator import HelpPaginator


class Iceteabot(commands.Bot):
    def __init__(self, *args, **kwargs):
        self.config: dict = kwargs.pop("config",{})
        self.name: str = self.config.get("name", "iceteabot")
        self.version = self.config.get("version", 1.0)
        self.default_prefix: str = self.config.get("default_prefix", "<<<")
        self.uptime: datetime.datetime = datetime.datetime.utcnow()
        self.command_stats: typing.Dict[Guild, typing.Dict[User, typing.Counter[Command, int]]] = {}
        self.owner: User = None
        self.cog_path: str = self.config.get("cogs_path", "cogs")
        self.error_logger: logging.Logger = None
        self.logger: logging.Logger = None
        self.client_id: str = None

        super(Iceteabot, self).__init__(
            command_prefix=commands.when_mentioned_or(self.default_prefix),
            activity=discord.Game(self.config.get("game", f"{self.default_prefix}help")),
            *args, **self.config)
        self.loop.create_task(self._initialize())
        self.aioconnection: ClientSession = ClientSession(json_serialize=ujson.dumps, loop=self.loop)
        self.remove_command("help")
        self.add_command(self._help)
        self.add_command(self.welcome)
        self.add_command(self._prefix)
        self.add_command(self.ping)

    def run(self, *args, **kwargs):
        if args:
            token = args[0]
        else:
            token = self.config['api_keys']['discord']
        return super(Iceteabot, self).run(token)

    def load_extension(self, name):
        return super(Iceteabot, self).load_extension(f"{self.cog_path}.{name}")

    def unload_extension(self, name):
        return super(Iceteabot, self).unload_extension(f"{self.cog_path}.{name}")

    def get_context(self, message, *, cls=IceTeaContext):
        return super(Iceteabot, self).get_context(message, cls=cls)

    async def logout(self):
        await self.aioconnection.close()
        await super(Iceteabot, self).logout()

    async def on_command_error(self, ctx: IceTeaContext, error):
        """Commands error handling method"""
        # Reports that a command is on cool down
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                f"This command is on cooldown! Hold your horses! >:c\nTry again in "
                f"**{int(error.retry_after)}** seconds")
        # Reports that the command is disabled
        elif isinstance(error, commands.errors.DisabledCommand):
            await ctx.send("That functionality is currently disabled")
        # Reports that the command cannot be handled inside a PM
        elif isinstance(error, commands.errors.NoPrivateMessage):
            await ctx.send("I am unable to processes this command inside a PM")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Sorry, you forgot to include ``{error.param}`` with that call, try again")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(
                f"Sorry, I could not do anything with what you provided me.\n"
                f"You can use ``{ctx.prefix}help {ctx.invoked_with}`` for more info")
        elif hasattr(ctx.cog, f"_{ctx.cog.__class__.__name__}__error"):
            return
        # Reports on non generic errors
        elif isinstance(error, commands.errors.CommandInvokeError):
            try:
                await ctx.message.add_reaction("\U000026a0")

                def check(reaction, reactor):
                    return ctx.message.id == reaction.message.id and reaction.emoji == "\U000026a0" and reaction.count > 1 \
                           and reactor == ctx.bot.owner

                try:
                    await ctx.bot.wait_for("reaction_add", check=check, timeout=30)
                    embed = discord.Embed(color=0xff0000, description='displays detailed error information',
                                          title='Iceteabot error log')
                    embed.add_field(name="Command used", value=f"{ctx.invoked_with}")
                    embed.add_field(name="Command author", value=f"{ctx.message.author.display_name}")
                    embed.add_field(name="args", value=ctx.kwargs or ctx.args)
                    embed.add_field(name="Error", value=error.original, inline=False)
                    embed.add_field(name="Log",
                                    value=f"```py\n{traceback.format_tb(error.original.__traceback__)[-1]}```")
                    embed.timestamp = datetime.datetime.utcnow()
                    debug_channel = ctx.bot.get_channel(360895354033537029)
                    if debug_channel is not None:
                        await debug_channel.send(embed=embed)
                    else:
                        await ctx.send(embed=embed, delete_after=10)
                    try:
                        await ctx.message.clear_reactions()
                        await ctx.message.delete()
                    except discord.Forbidden:
                        pass
                    except discord.HTTPException:
                        pass
                except asyncio.TimeoutError:
                    try:
                        await ctx.message.clear_reactions()
                        await ctx.message.delete()
                    except discord.Forbidden:
                        pass
                    except discord.HTTPException:
                        pass
            except discord.Forbidden:
                pass

    def setup_logging(self):
        self.logger = logging.getLogger("discord")
        self.logger.setLevel(logging.INFO)
        handler = logging.FileHandler(filename="data/iceteabot.log", encoding='utf-8', mode='w')
        handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
        self.logger.addHandler(handler)
        self.error_logger = logging.getLogger("errors")
        self.error_logger.setLevel(logging.INFO)
        handler = logging.FileHandler(filename="data/error.log", encoding='utf-8', mode='w')
        handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
        self.error_logger.addHandler(handler)

    async def _initialize(self):
        await self.wait_until_ready()
        application_info: discord.AppInfo = await self.application_info()
        self.client_id = application_info.id
        self.owner = application_info.owner
        for guild in self.guilds:
            self.command_stats[guild] = {member: Counter() for member in guild.members if not member.bot}

        cogs = self.config.get("extensions")
        if cogs == "*":
            startup_extensions = [f"{os.path.basename(ext)[:-3]}"
                                  for ext in glob.glob("cogs/*.py")]
        elif isinstance(cogs, list):
            startup_extensions = cogs
        else:
            startup_extensions = []

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

    @commands.command()
    async def _help(self, ctx, *, command: str = None):
        """Shows help about a command for the bot"""
        if command is None:
            p = await HelpPaginator.from_bot(ctx)
        else:
            entity = self.get_cog(command) or self.get_command(command)
            if entity is None:
                clean = command.replace('@', '@\u200b')
                return await ctx.send(f'Command or category "{clean}" not found.')
            elif isinstance(entity, commands.Command):
                p = await HelpPaginator.from_command(ctx, entity)
            else:
                p = await HelpPaginator.from_cog(ctx, entity)
        await p.paginate()

    @staticmethod
    @commands.command(name="hi", aliases=['hello'])
    async def welcome(ctx):
        """Display's a welcome message"""
        await ctx.send(f"Hello! I am a bot made by {ctx.bot.owner}")

    @staticmethod
    @commands.command(name="prefix")
    async def _prefix(ctx):
        """Display's the bot's default prefix"""
        await ctx.send(f"My Current prefix is {ctx.bot.default_prefix} or you can always mention me.")

    @staticmethod
    @commands.command()
    async def ping(ctx):
        """displays the bot's latency with discord"""
        await ctx.send(f"Current ping is: **{round(ctx.bot.latency, 2)} seconds**")
