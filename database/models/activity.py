import dataclasses
import typing

import discord

from database.models.model import Model


@dataclasses.dataclass()
class Activity(Model):
    guild: int = None
    status: str = None
    role: int = None

    def get_role(self) -> typing.Optional[discord.Role]:
        return discord.utils.get(self.bot.get_guild(self.guild).roles, id=self.role)

    @classmethod
    def setup_table(cls) -> str:
        return 'CREATE TABLE IF NOT EXISTS activities(id bigint primary key,' \
               'guild bigint references guilds(id) on DELETE CASCADE ,' \
               'role bigint);'
