import typing

import discord
from discord.ext import commands
from discord.ext.commands import Context

from database import models


class IceTeaContext(Context):
    def __init__(self, **attrs):
        super().__init__(**attrs)
        self.bot: "Iceteabot" = self.bot
        self.author_data: typing.Optional[typing.Union[models.User, models.Member]] = None

    @property
    def prefix_data(self) -> "models.Prefix":
        if self.guild_data is not None:
            return self.guild_data.prefixes.get(self.prefix)

    @property
    def invoked_command(self) -> commands.Command:
        return self.bot.get_command(self.invoked_with)

    @property
    def guild_data(self) -> "models.Guild":
        if self.guild:
            return self.bot.get_guild_data(self.guild.id)

    def get_guild_data(self, guild: int = None) -> "models.Guild":
        return self.bot.get_guild_data(guild)

    async def get_author_data(self):
        return await self.get_user_data(self.author)

    async def get_user_data(self, user: typing.Union[discord.Member, discord.User]) -> typing.Union[
        "models.Member", "models.User"]:
        if hasattr(user, "guild"):
            guild = self.get_guild_data(user.guild.id)
            if guild:
                return await guild.get_member(user.id)
        else:
            return await self.bot.sql.get_user(user.id)

    def dispatch_error(self, error: Exception):
        self.bot.dispatch("command_error", self, error)

    async def clean_content(self, argument, *, fix_channel_mentions: bool = True, use_nicknames: bool = True,
                            escape_markdown: bool = False) -> str:
        return await commands.clean_content(fix_channel_mentions=fix_channel_mentions, use_nicknames=use_nicknames,
                                            escape_markdown=escape_markdown).convert(self, argument)

    async def send_success(self):
        await self.send("\U00002705", delete_after=10)


if __name__ == '__main__':
    from utils.iceteabot import Iceteabot
