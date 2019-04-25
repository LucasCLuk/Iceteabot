import dataclasses
import datetime

from database.models.model import Model


@dataclasses.dataclass()
class Task(Model):
    author: int = None
    created: datetime.datetime = dataclasses.field(default_factory=datetime.datetime.utcnow)
    content: str = None
    finished: bool = False

    @classmethod
    def setup_table(cls) -> str:
        return 'CREATE TABLE IF NOT EXISTS tasks(id bigint primary key ,' \
               'author bigint,' \
               'created timestamp,' \
               'content text,' \
               'finished boolean);'
