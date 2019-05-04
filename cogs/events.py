import discord
from discord.ext import commands

from database import models
from utils.iceteacontext import IceTeaContext


class Events(commands.Cog):

    def __init__(self, bot):
        self.bot: "Iceteabot" = bot

    @commands.Cog.listener()
    async def on_command_completion(self, ctx: IceTeaContext):
        if not isinstance(ctx.channel, discord.abc.PrivateChannel):
            await ctx.guild_data.call_command(ctx)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        try:
            await self.bot.add_guild(guild)
        except:
            pass
        try:
            await self.bot.update_discord_bots()
        except:
            pass

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        await self.bot.remove_guild(guild.id)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if not member.bot:
            guild_data: models.Guild = self.bot.get_guild_data(member.guild.id)
            await guild_data.add_member(member.id)
            join_channel = self.bot.get_channel(guild_data.welcome_channel)
            if join_channel:
                if guild_data.welcome_message:
                    await join_channel.send(guild_data.welcome_message)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if not member.bot:
            guild_data: models.Guild = self.bot.get_guild_data(member.guild.id)
            await guild_data.remove_member(member.id)
            leaving_channel = self.bot.get_channel(guild_data.leaving_channel)
            if leaving_channel:
                if guild_data.leaving_message:
                    await leaving_channel.send(guild_data.leaving_message)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if not before.bot:
            if before.nick != after.nick and after.nick is not None:
                await self.bot.get_guild_data(after.guild.id).add_member_nickname(after.id, after.nick)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild and not message.author.bot:
            await self.bot.sql.update_member_last_spoke(message.author.id, message.guild.id, message.created_at)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.emoji.is_unicode_emoji() and self.bot.owner_id is not None:
            if all([payload.channel_id == 384410040880201730, payload.user_id == self.bot.owner_id,
                    str(payload.emoji) == "\U0000274c"]):
                channel = self.bot.get_channel(payload.channel_id)
                if channel is not None:
                    message = await channel.get_message(payload.message_id)
                    if payload.message_id is not None:
                        await message.delete()


def setup(bot):
    bot.add_cog(Events(bot))


if __name__ == '__main__':
    from utils.iceteabot import Iceteabot
