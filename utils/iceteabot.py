import asyncio
import datetime
import glob
import logging
import os
import traceback
import typing

import asyncpg
import discord
import psutil
import ujson
from aiohttp import ClientSession
from discord.ext import commands

from database import models
from database.sqlclient import SqlClient
from utils.help import IceHelpCommand
from utils.iceteacontext import IceTeaContext


class Iceteabot(commands.Bot):
    def __init__(self, *args, **kwargs):
        self.config: dict = kwargs.pop("config", {})
        super(Iceteabot, self).__init__(
            command_prefix=self.get_guild_prefix,
            help_command=IceHelpCommand(),
            status=discord.Status.idle,
            case_insensitive=True,
            *args, **self.config)
        self.debug: bool = self.config.get("debug", True)
        self.name: str = self.config.get("name", "iceteabot")
        self.version = self.config.get("version", 1.0)
        self.default_prefix: str = self.config.get("default_prefix", "<<<")
        self.uptime: datetime.datetime = datetime.datetime.utcnow()
        self.owner: typing.Optional[models.User] = None
        self.cog_path: str = self.config.get("cogs_path", "cogs")
        self.client_id: typing.Optional[str] = None
        self.aioconnection: ClientSession = ClientSession(json_serialize=ujson.dumps, loop=self.loop)
        self._database_loaded = asyncio.Event(loop=self.loop)
        self.sql: typing.Optional[SqlClient] = None
        self.guild_data: typing.Dict[int, models.Guild] = {}
        self.logger: typing.Optional[logging.Logger] = None
        self.error_logger: typing.Optional[logging.Logger] = None
        self.data_base_built = False
        self.add_check(self.guild_black_list)
        self.add_check(lambda ctx: ctx.bot.data_base_built)
        self.add_command(self.welcome_command)
        self.add_command(self.ping_command)
        self._before_invoke = self._create_user_data
        self.loop.create_task(self._initialize())

    # noinspection PyUnresolvedReferences
    def run(self, *args, **kwargs):
        if args:
            token = args[0]
        else:
            token = self.config['api_keys']['discord']
        try:
            import uvloop
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        except ImportError:
            pass
        return super(Iceteabot, self).run(token)

    def reload_extension(self, name):
        return super(Iceteabot, self).reload_extension(f"{self.cog_path}.{name}")

    def get_context(self, message, *, cls=IceTeaContext):
        return super(Iceteabot, self).get_context(message, cls=cls)

    async def wait_until_ready(self):
        await asyncio.wait([
            super(Iceteabot, self).wait_until_ready(),
            self._database_loaded.wait()
        ], return_when=asyncio.ALL_COMPLETED)

    async def close(self):
        await self.aioconnection.close()
        await self.sql.pool.close()
        await super(Iceteabot, self).close()
        if not self.debug:
            exit(1)  # This is so that the system manager will properly restart it.

    async def on_command_error(self, ctx: IceTeaContext, error: Exception):
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
            finally:
                try:
                    from sentry_sdk import capture_exception
                    capture_exception(error)
                except ImportError:
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
        self.setup_raven()

    def setup_raven(self):
        try:
            from sentry_sdk import init, capture_message
            from sentry_sdk.integrations.logging import LoggingIntegration
            sentry_logging = LoggingIntegration(
                level=logging.INFO,  # Capture info and above as breadcrumbs
                event_level=logging.ERROR  # Send errors as events
            )
            init(self.config['api_keys']['sentry'], integrations=[sentry_logging])
        except ImportError:
            return

    async def setup_database(self):
        try:
            self.sql = SqlClient(await asyncpg.create_pool(**self.config['database']), self)
            await self.sql.setup()
        except:
            exit(1)
        await self.sql.add_users(self.users)
        guilds = await self.sql.get_all_guilds()
        self.guild_data.update({guild.id: guild for guild in guilds})
        for guild in self.guilds:
            if guild.id not in self.guild_data:
                new_guild = models.Guild(self.sql, guild.id)
                self.guild_data[guild.id] = new_guild
                await new_guild.save()
        self._database_loaded.set()
        self.data_base_built = True

    async def _initialize(self):
        try:
            self.setup_logging()
            await self._ready.wait()
            application_info: discord.AppInfo = await self.application_info()
            self.client_id = application_info.id
            self.owner = application_info.owner
            await self.setup_database()
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
                    self.load_extension(f"{self.cog_path}.{extension}")
                except Exception as e:
                    exc = '{}: {} on cog: {}'.format(type(e).__name__, e, extension)
                    print(exc)

            print(f"Successfully logged in as {self.user}\n" +
                  f"Using version {discord.__version__} of discord.py\n" +
                  f"Using {psutil.Process().memory_full_info().uss / 1024 ** 2} of ram\n" +
                  f"loaded {len(self.extensions)} cogs\n" +
                  f"{'-' * 15}")
            await self.change_presence(activity=discord.Game(name="waiting for orders"))
        except Exception as e:
            try:
                from sentry_sdk import capture_exception
                capture_exception(e)
                exit(1)
            except ImportError:
                pass

    @staticmethod
    @commands.command(name="hi", aliases=['hello'])
    async def welcome_command(ctx):
        """Display's a welcome message"""
        await ctx.send(f"Hello! I am a bot made by {ctx.bot.owner}")

    @staticmethod
    @commands.command(name="ping")
    async def ping_command(ctx):
        """displays the bot's latency with discord"""
        await ctx.send(f"Current ping is: **{round(ctx.bot.latency, 2)} seconds**")

    @staticmethod
    async def guild_black_list(ctx):
        if ctx.guild is None:
            return True
        return ctx.channel.id not in ctx.guild_data.blocked_channels

    @staticmethod
    async def get_guild_prefix(iceteabot, message):
        if message.guild is None:
            return commands.when_mentioned_or(*iceteabot.config['default_prefix'])(iceteabot, message)
        else:
            guild_data: models.Guild = iceteabot.guild_data.get(message.guild.id)
            if guild_data:
                if guild_data.prefixes:
                    return commands.when_mentioned_or(*guild_data.prefixes.keys())(iceteabot, message)
                else:
                    return commands.when_mentioned(iceteabot, message)
            else:
                return commands.when_mentioned(iceteabot, message)

    @staticmethod
    async def _create_user_data(ctx: "IceTeaContext"):
        await ctx.guild_data.add_member(ctx.author.id)
        ctx.author_data = await ctx.get_user_data(ctx.author)
