import typing
from collections import Counter

from discord import User, Guild
from discord.ext.commands import Context, Command


class IceTeaContext(Context):
    def __init__(self, **attrs):
        super().__init__(**attrs)
        self.bot: "Iceteabot" = self.bot

    @property
    def command_stats(self) -> typing.Dict[User, typing.Counter[Command]]:
        if self.guild:
            return self.bot.command_stats[self.guild]
        else:
            return Counter()

    @property
    def author_command_stats(self) -> Counter:
        if self.guild:
            return self.command_stats[self.author]

    def get_author_stats(self, user: User = None):
        user = user or self.author
        return self.command_stats[user]

    def get_guild_command_total(self, guild: Guild) -> int:
        guild_stats = self.bot.command_stats[guild]
        return sum(sum(m.values()) for m in guild_stats.values())

    @property
    def guild_commands_used_count(self) -> int:
        return self.get_guild_command_total(self.guild)

    @property
    def total_commands_used_count(self):
        total = 0
        for guild in self.bot.command_stats:
            total += self.get_guild_command_total(guild)
        return total


if __name__ == '__main__':
    from iceteabot import Iceteabot
