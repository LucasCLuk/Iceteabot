import discord
from discord.ext import commands

from utils.iceteacontext import IceTeaContext


class Events(commands.Cog):

    def __str__(self):
        return self.__class__.__name__

    @commands.Cog.listener()
    async def on_command_completion(self,ctx: IceTeaContext):
        if not isinstance(ctx.channel, discord.abc.PrivateChannel):
            ctx.author_command_stats[ctx.command] += 1


def setup(bot):
    bot.add_cog(Events())
