import dataclasses
import datetime
import typing

from database.models.nickname import NickName
from database.models.user import User


@dataclasses.dataclass()
class Member(User):
    PRIMARY_KEY = ('id', 'guild')
    guild: int = None
    last_spoke: datetime.datetime = None
    level: int = None
    reputation: str = None
    experience: int = 0
    achievement_points: int = 0
    wallet: int = 0
    administrator: bool = False

    @classmethod
    def get_fields(cls):
        return [field for field in dataclasses.fields(Member) if field not in dataclasses.fields(User) or
                field.name == "id"]

    @classmethod
    def setup_table(cls) -> str:
        return 'CREATE TABLE IF NOT EXISTS members(id bigint ,' \
               'guild bigint references guilds(id) on DELETE CASCADE ,' \
               'last_spoke timestamp,' \
               'level integer,' \
               'reputation text,' \
               'experience integer,' \
               'achievement_points integer,' \
               'wallet integer,' \
               'administrator boolean, ' \
               'PRIMARY KEY (id,guild));'

    async def get_nicknames(self) -> typing.List["NickName"]:
        nicknames = self.client.get_all(NickName,
                                        "SELECT * FROM nicknames WHERE member = $1 and guild = $2 "
                                        "ORDER BY changed DESC LIMIT 5;", self.id, self.guild)
        return [nick async for nick in nicknames]
