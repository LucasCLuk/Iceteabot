import dataclasses
import datetime
import typing

import discord

from database.models.model import Model


@dataclasses.dataclass()
class ReactionRole(Model):
    message_id: int = None
    emoji: str = None
    guild: int = None
    created: datetime.datetime = dataclasses.field(default_factory=datetime.datetime.utcnow)
    author: int = None
    role: int = None

    def get_guild(self) -> typing.Optional[discord.Guild]:
        return self.bot.get_guild(self.guild)

    def get_role(self) -> typing.Optional[discord.Role]:
        guild = self.get_guild()
        if guild:
            return guild.get_role(self.role)

    @classmethod
    def setup_table(cls) -> str:
        return """
        CREATE TABLE IF NOT EXISTS reaction_role(
        id bigint primary key ,
        message_id bigint,
        emoji VARCHAR(256),
        guild bigint references guilds(id) on DELETE CASCADE,
        created timestamp,
        author bigint,
        role bigint,
        unique (message_id,emoji)
        )
        """
