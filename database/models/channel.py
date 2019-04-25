import dataclasses
import datetime

from database.models.model import Model


@dataclasses.dataclass()
class Channel(Model):
    guild: int = None
    created: datetime.datetime = dataclasses.field(default_factory=datetime.datetime.utcnow)
    blocker: int = None
    reason: str = None

    @classmethod
    def setup_table(cls) -> str:
        return 'CREATE TABLE IF NOT EXISTS channels(id bigint primary key ,' \
               'guild bigint references guilds(id) on DELETE CASCADE ,' \
               'blocker bigint,' \
               'reason text);'
