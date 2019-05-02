# Built-in Libs
import asyncio
import io
import os
import textwrap
import time
import traceback
from contextlib import redirect_stdout

import discord
import ujson
from discord.ext import commands

from utils import time as utils_time
from utils.formats import TabularData, Plural
from utils.iceteacontext import IceTeaContext


# The owner class, commands here can only be executed by the owner of the bot
class Owner(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        return await ctx.bot.is_owner(ctx.author)

    @staticmethod
    def cleanup_code(content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')

    @staticmethod
    def get_syntax_error(e):
        if e.text is None:
            return f'```py\n{e.__class__.__name__}: {e}\n```'
        return f'```py\n{e.text}{"^":>{e.offset}}\n{e.__class__.__name__}: {e}```'

    @commands.command(hidden=True, aliases=['status', 'chstat', "chstatus", 'botgame'])
    async def changestatus(self, ctx: IceTeaContext, *, game):
        """Changes the game the bot is playing
        can only be used by admins"""
        await self.bot.change_presence(game=discord.Game(name=game))
        await ctx.send("Now playing ``{0}``".format(game))

    @commands.command(hidden=True, name='eval')
    async def _eval(self, ctx: IceTeaContext, *, body: str):
        """Evaluates a code"""

        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            '_guild_id': ctx.guild,
            'message': ctx.message,
        }

        env.update(globals())

        body = self.cleanup_code(body)
        stdout = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            return await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')

        func = env['func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction('\u2705')
            except:
                pass

            if ret is None:
                if value:
                    await ctx.send(f'```py\n{value}\n```')
            else:
                self._last_result = ret
                if len(f"{value}{ret}") >= 2000:
                    data = io.StringIO(f"{value}{ret}")
                    await ctx.send("Output too long, sending a file instead",
                                   file=discord.File(fp=data, filename="output.txt"))
                    data.close()
                    del data
                    return
                await ctx.send(f'```py\n{value}{ret}\n```')

    @commands.command(hidden=True)
    async def sql(self, ctx: "IceTeaContext", *, query: str):
        """Run some SQL."""
        # the imports are here because I imagine some people would want to use
        # this cog as a base for their other cog, and since this one is kinda
        # odd and unnecessary for most people, I will make it easy to remove
        # for those people.

        query = self.cleanup_code(query)

        is_multistatement = query.count(';') > 1
        if is_multistatement:
            # fetch does not support multiple statements
            strategy = ctx.bot.sql.pool.execute
        else:
            strategy = ctx.bot.sql.pool.fetch

        try:
            start = time.perf_counter()
            results = await strategy(query)
            dt = (time.perf_counter() - start) * 1000.0
        except Exception:
            return await ctx.send(f'```py\n{traceback.format_exc()}\n```')

        rows = len(results)
        if is_multistatement or rows == 0:
            return await ctx.send(f'`{dt:.2f}ms: {results}`')

        headers = list(results[0].keys())
        table = TabularData()
        table.set_columns(headers)
        table.add_rows(list(r.values()) for r in results)
        render = table.render()

        fmt = f'```\n{render}\n```\n*Returned {Plural(row=rows)} in {dt:.2f}ms*'
        if len(fmt) > 2000:
            fp = io.BytesIO(fmt.encode('utf-8'))
            await ctx.send('Too many results...', file=discord.File(fp, 'results.txt'))
        else:
            await ctx.send(fmt)

    @commands.command(name="chavatar")
    async def avatar(self, ctx: IceTeaContext, link=None):
        """Edits the bot's avatar. Can only be used by owner can provide a link or attachment"""
        if link is None:
            if ctx.message.attachments:
                attachment_link: discord.Attachment = ctx.message.attachments[0]
                link = attachment_link.url
        if link is not None:
            async with ctx.bot.aioconnection.get(link) as response:
                try:
                    await ctx.bot.user.edit(avatar=await response.read())
                except:
                    await ctx.send("Unable to use this link")
            await ctx.send("Avatar Changed successfully")
        else:
            await ctx.send("No data provided. Either pass a link to an image or attach one")

    @commands.command()
    async def botname(self, ctx, name: str = None):
        """Changes the bot's username
        :name the new name to be used"""
        # Edits the bot name using the arg :name:
        await ctx.bot.user.edit(username=name)
        # Responds that the mission was a success
        await ctx.send("Name changed successfully")

    @commands.command(hidden=True, no_pm=True)
    async def botnick(self, ctx: IceTeaContext, *, name: str = None):
        """Changes the bot's nickname
        :name the new name to be used"""
        # Edits the bot name using the arg :name:
        try:
            await ctx.me.edit(nick=name)
            # Responds that the mission was a success
            await ctx.send("Name changed successfully")
        except discord.Forbidden:
            await ctx.send("I do not have permissions to edit my name :cry:")

    @commands.command(hidden=True)
    async def load(self, ctx: IceTeaContext, *, cog_name: str):
        """Loads a module."""
        try:
            ctx.bot.load_extension(cog_name.lower())
        except Exception as e:
            await ctx.send('\N{PISTOL}')
            await ctx.send('{}: {}'.format(type(e).__name__, e))
        else:
            await ctx.send('\N{OK HAND SIGN}')

    @commands.command(hidden=True)
    async def unload(self, ctx: IceTeaContext, *, cog_name: str):
        """Unloads a module."""
        try:
            ctx.bot.unload_extension(cog_name.lower())
        except Exception as e:
            await ctx.send('\N{PISTOL}')
            await ctx.send('{}: {}'.format(type(e).__name__, e))
        else:
            await ctx.send('\N{OK HAND SIGN}')

    @commands.command(name='reloadall', hidden=True)
    async def _reloadall(self, ctx: IceTeaContext):
        """Attempts to reload all the cogs at once"""
        for cog in ctx.bot.extensions:
            try:
                ctx.bot.reload_extension(cog)
            except Exception as e:
                await ctx.send('\N{PISTOL}')
                await ctx.send('{}: {}'.format(type(e).__name__, e))

    @commands.command(name='viewcogs', hidden=True)
    async def _viewcogs(self, ctx: IceTeaContext):
        await ctx.send("\n".join(cog for cog in ctx.bot.extensions))

    @commands.command(hidden=True, aliases=['shutoff', 'quit', 'logout', 'wq!'])
    async def botshutdown(self, ctx: IceTeaContext):
        await ctx.send("Bot is shutting down")
        await asyncio.sleep(1)
        await ctx.send("Good-bye...")
        await ctx.bot.logout()

    @commands.command(hidden=True, name="cogstatus", aliases=['cstatus'])
    async def _cog_status(self, ctx: IceTeaContext):
        """Displays all currently loaded cogs"""
        cog_names = [cog for cog in ctx.bot.extensions]
        msg = "\n".join(cog_names)
        embed = discord.Embed(description="Cog status", title=f"{ctx.bot.name} Cog Status")
        embed.set_thumbnail(url="http://i.imgur.com/5BFecvA.png")
        embed.add_field(name="Cogs loaded:",
                        value=msg
                        )
        await ctx.send(embed=embed)

    @commands.command(name="reload")
    async def _reload(self, ctx: IceTeaContext, *, extension):
        try:
            ctx.bot.reload_extension(extension)
        except Exception as e:
            await ctx.send('\N{PISTOL}', delete_after=5)
            await ctx.send('{}: {}'.format(type(e).__name__, e))
        else:
            await ctx.send('\N{OK HAND SIGN}')

    @commands.command(aliases=['do'])
    async def repeatcmd(self, ctx: IceTeaContext, amount: int, command_name, *, command_args):
        """Repeats X command Y times"""
        command = ctx.bot.get_command(command_name)
        if amount > 20:
            return await ctx.send("You want me to repeat a command more than 20 times? You crazy...")
        if command is not None:
            for x in range(0, amount):
                await ctx.invoke(command, command_args)

    @commands.command(name="leaveguild")
    async def leave_guild(self, ctx: IceTeaContext, target_guild: int):
        guild_obj = ctx.bot.get_guild(target_guild)
        if guild_obj is not None:
            await guild_obj.leave()
            await ctx.bot.owner.send(f"Left guild {guild_obj.name}")
        else:
            await ctx.bot.owner.send(f"Could not find a guild with that ID")

    @commands.command(name="nuke")
    async def nuke_this_shit(self, ctx: IceTeaContext):
        """Nukes the bot, and destroys the files"""

    @commands.command(name="updateconfig")
    async def update_config(self, ctx: IceTeaContext):
        """Updates the bot's config file"""
        with open(os.path.join('data', 'config.json')) as file:
            ctx.bot.config = ujson.load(file)
            await ctx.message.add_reaction('\u2705')

    @commands.command(name="updatedbots")
    async def update_dbots(self, ctx: IceTeaContext):
        """Sends an update request to discordbots"""
        response = await ctx.bot.update_discord_bots()
        if response == 200:
            await ctx.message.add_reaction("\u2705")

    @commands.command()
    async def newguilds(self, ctx: IceTeaContext, *, count=5):
        """Tells you the newest guilds the bot has joined.

        The count parameter can only be up to 50.
        """
        count = max(min(count, 50), 5)
        guilds = sorted(ctx.bot.guilds, key=lambda m: m.me.joined_at, reverse=True)[:count]

        e = discord.Embed(title='New Guilds', colour=discord.Colour.green())

        for guild in guilds:
            body = f'Joined {utils_time.human_timedelta(guild.me.joined_at)}'
            e.add_field(name=f'{guild.name} (ID: {guild.id})', value=body, inline=False)

        await ctx.send(embed=e)


def setup(bot):
    """Standard setup method for cog"""
    bot.add_cog(Owner(bot))
