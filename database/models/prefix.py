import dataclasses
import datetime

from database.models.model import Model


@dataclasses.dataclass()
class Prefix(Model):
    guild: int = None
    prefix: str = None
    author: int = None
    uses: int = 0
    created: datetime.datetime = dataclasses.field(default_factory=datetime.datetime.utcnow)

    def __str__(self):
        return self.prefix

    @classmethod
    def setup_table(cls) -> str:
        return 'CREATE TABLE IF NOT EXISTS prefixes(id bigint primary key,' \
               'guild bigint references guilds(id) on DELETE CASCADE ,' \
               'prefix text,' \
               'author bigint,' \
               'uses integer,' \
               'created timestamp, ' \
               'unique(guild,prefix));'

    async def use(self):
        self.uses += 1
        await self.client.execute("UPDATE prefixes SET uses = uses + 1 WHERE id = $1", self.id)
