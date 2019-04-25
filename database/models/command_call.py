import dataclasses
import datetime

from database.models.model import Model


@dataclasses.dataclass()
class CommandCall(Model):
    command: str = None
    guild: int = None
    author: int = None
    called: datetime.datetime = dataclasses.field(default_factory=datetime.datetime.utcnow)

    @classmethod
    def setup_table(cls) -> str:
        return 'CREATE TABLE IF NOT EXISTS commands (' \
               'id bigint primary key ,' \
               'command text,' \
               'guild bigint references guilds(id) on DELETE CASCADE ,' \
               'author bigint ,' \
               'called timestamp);'
