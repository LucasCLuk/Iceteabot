import dataclasses
import typing

from database.models.model import Model


@dataclasses.dataclass()
class User(Model):
    league: str = None
    pubg: str = None
    osu: str = None
    location: str = None
    blocked: bool = False

    @classmethod
    def setup_table(cls) -> str:
        return f"CREATE TABLE IF NOT EXISTS users(id bigint primary key, " \
            f"league text," \
            f"pubg text ," \
            f"osu text, " \
            f"location text," \
            f"blocked boolean);"

    async def get_all_tasks(self) -> typing.List["Task"]:
        return [task async for task in self.client.get_all(Task, "SELECT * FROM tasks where author = $1", self.id)]

    async def get_unfinished_tasks(self) -> typing.List["Task"]:
        return [task async for task in
                self.client.get_all(Task, "SELECT * FROM tasks where author = $1 and finished = False", self.id)]

    async def get_finished_tasks(self) -> typing.List["Task"]:
        return [task async for task in
                self.client.get_all(Task, "SELECT * FROM tasks where author = $1 and finished = True", self.id)]

    async def add_task(self, content: str) -> "Task":
        new_task = Task(self.client, author=self.id, content=content)
        await new_task.save()
        return new_task

    async def finish_task(self, task_id: int):
        await self.client.execute("UPDATE tasks SET finished = true where id = $1", task_id)

    async def delete_task(self, task_id: int):
        await self.client.execute("DELETE FROM tasks where id = $1", task_id)


if __name__ == '__main__':
    from . import Task
