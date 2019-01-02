import asyncio
import datetime
import traceback
import discord
from discord.ext import commands

from iceteacontext import IceTeaContext


class Events:

    @staticmethod
    async def on_command_completion(ctx: IceTeaContext):
        if not isinstance(ctx.channel, discord.abc.PrivateChannel):
            ctx.author_command_stats[ctx.command] += 1

    @staticmethod
    async def on_command_error(ctx: IceTeaContext, error):
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


def setup(bot):
    bot.add_cog(Events())
