import dataclasses
import datetime
import typing

from database.models.model import Model


@dataclasses.dataclass()
class Tag(Model):
    author: int = None
    title: str = None
    content: str = None
    created: datetime.datetime = dataclasses.field(default_factory=datetime.datetime.utcnow)
    last_edited: datetime.datetime = None
    guild: int = None
    alias = None
    count: int = 0

    @classmethod
    def setup_table(cls) -> str:
        return 'CREATE TABLE IF NOT EXISTS tags(id bigint primary key ,' \
               'author bigint,' \
               'title text,' \
               'content text,' \
               'created timestamp,' \
               'last_edited timestamp,' \
               'guild bigint references guilds(id) on DELETE CASCADE , ' \
               'foreign key (author,guild) references members(id,guild) ON DELETE set null ,' \
               'unique (title,guild));'

    async def get_aliases(self) -> typing.List["Tag"]:
        return [alias async for alias in
                self.client.get_all(Tag, "SELECT * FROM tagslink WHERE tag = $1", self.id)]

    async def edit(self, *, content: str):
        self.content = content
        self.last_edited = datetime.datetime.utcnow()
        await self.save()


@dataclasses.dataclass()
class TagLookup(Model):
    title: str = None
    author: int = None
    guild: int = None
    tag: int = None
    count: int = 0

    @classmethod
    def setup_table(cls) -> str:
        return 'CREATE TABLE IF NOT EXISTS tagslink (' \
               'id bigint primary key,' \
               'title text,' \
               'author bigint,' \
               'guild bigint REFERENCES guilds(id) on DELETE CASCADE ,' \
               'tag bigint references tags(id) on DELETE CASCADE, count bigint, ' \
               'FOREIGN KEY (author,guild) REFERENCES members(id,guild) ON DELETE SET NULL );'
