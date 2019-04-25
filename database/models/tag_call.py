import dataclasses
import datetime

from database.models.model import Model


@dataclasses.dataclass()
class TagCall(Model):
    tag_id: int = None
    author: int = None
    channel: int = None
    guild: int = None
    called: datetime.datetime = dataclasses.field(default_factory=datetime.datetime.utcnow)

    @classmethod
    def setup_table(cls) -> str:
        return 'CREATE TABLE IF NOT EXISTS tagcalls(id SERIAL PRIMARY KEY,' \
               'tag_id bigint,' \
               'author bigint,' \
               'channel bigint,' \
               'guild bigint references  guilds(id) on DELETE CASCADE,' \
               'called timestamp, FOREIGN KEY (author,guild) REFERENCES members(id,guild) on DELETE CASCADE );'
