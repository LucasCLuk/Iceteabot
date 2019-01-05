import discord

from utils.iceteacontext import IceTeaContext


class Events:

    @staticmethod
    async def on_command_completion(ctx: IceTeaContext):
        if not isinstance(ctx.channel, discord.abc.PrivateChannel):
            ctx.author_command_stats[ctx.command] += 1


def setup(bot):
    bot.add_cog(Events())
