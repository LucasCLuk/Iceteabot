import dataclasses
import datetime

from database.models.model import Model


@dataclasses.dataclass()
class FAQ(Model):
    guild: int = None
    author: int = None
    question: str = None
    answer: str = None
    created_at: datetime.datetime = dataclasses.field(default_factory=datetime.datetime.utcnow)
    uses: int = 0

    @classmethod
    def setup_table(cls) -> str:
        return 'CREATE TABLE IF NOT EXISTS faqs(id bigint primary key ,' \
               'guild bigint references guilds(id) on DELETE CASCADE ,' \
               'author bigint,' \
               'question text,' \
               'answer text,' \
               'created_at timestamp, ' \
               'uses int);'
