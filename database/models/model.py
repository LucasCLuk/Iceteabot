import dataclasses
import typing


class Table:
    PRIMARY_KEY: typing.Tuple[str] = ("id",)
    IGNORED_FIELDS: typing.List[str] = dataclasses.field(default_factory=lambda: ["client", "bot"])


@dataclasses.dataclass()
class Model(Table):
    client: "SqlClient" = dataclasses.field(hash=False, compare=False, repr=False)
    id: int = None

    def __post_init__(self):
        if not self.id and self.client:
            self.id = next(self.client.generator)

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

    @property
    def data(self) -> dict:
        return {field.name: getattr(self, field.name, None) for field in self.get_fields()}

    @property
    def bot(self):
        return self.client.bot

    @property
    def values(self) -> typing.ValuesView:
        return self.data.values()

    @classmethod
    def setup_table(cls) -> str:
        raise NotImplementedError

    @classmethod
    def get_fields(cls) -> typing.List[dataclasses.Field]:
        fields = []
        for key in list(dataclasses.fields(cls)):
            key_name = key.name
            if not any([key_name.startswith("_"), key_name.isupper(), key_name in ['client', 'bot']]):
                fields.append(key)
        return fields

    async def refresh(self, data):
        fields = dataclasses.fields(self)
        for field, value in fields.items():
            setattr(self, field.name, data[field.name])

    async def save(self):
        return await self.client.update(self)

    async def delete(self):
        return await self.client.delete(self)


if __name__ == '__main__':
    from database.sqlclient import SqlClient
