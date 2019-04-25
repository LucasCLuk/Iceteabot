import asyncio
import dataclasses
import datetime

from database.models.model import Model
from utils import time


@dataclasses.dataclass()
class Reminder(Model):
    user: int = None
    message: str = None
    guild: int = None
    time: datetime.datetime = None
    channel: int = None
    event: str = None
    delta: datetime.datetime = None
    _task: asyncio.Task = dataclasses.field(default=None, init=False, repr=False, compare=False)

    @property
    def task(self):
        return self._task

    @property
    def human_delta(self):
        return time.human_timedelta(self.time)

    @property
    def jump_url(self):
        guild_id = "@me" if self.guild is None else self.guild
        return f"https://discordapp.com/channels/{guild_id}/{self.channel}/{self.id}"

    async def _task_func(self):
        if self.delta < datetime.datetime.utcnow():
            return await self.delete()
        difference = self.delta - datetime.datetime.utcnow()
        await asyncio.sleep(difference.total_seconds())
        self.bot.dispatch(self.event, self)

    async def start(self):
        self._task = self.bot.loop.create_task(self._task_func())

    def cancel(self):
        if self.task:
            return self.task.cancel()

    @classmethod
    def setup_table(cls) -> str:
        return 'CREATE TABLE IF NOT EXISTS reminders( ' \
               'id bigint primary key ,' \
               '"user" bigint references users(id) on DELETE CASCADE ,' \
               'message text, ' \
               'guild bigint REFERENCES guilds(id) on DELETE CASCADE NULL,' \
               'time timestamp,' \
               'channel bigint,' \
               'event text,' \
               'delta timestamp);'
