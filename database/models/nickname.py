import dataclasses
import datetime

from database.models.model import Model


@dataclasses.dataclass()
class NickName(Model):
    member: int = None
    nickname: str = None
    changed: datetime.datetime = dataclasses.field(default_factory=datetime.datetime.utcnow)
    guild: int = None

    def __str__(self):
        return self.nickname

    @classmethod
    def setup_table(cls) -> str:
        return 'CREATE TABLE IF NOT EXISTS nicknames(id bigint primary key,' \
               'member bigint,' \
               'foreign key (member,guild) references members(id,guild) ON DELETE CASCADE ,' \
               'nickname text,' \
               'changed timestamp,' \
               'guild bigint references guilds(id));'
