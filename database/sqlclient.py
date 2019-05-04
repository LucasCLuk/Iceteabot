import datetime
import typing

import asyncpg
import discord

from database import models
from utils.snowflake import generator

RESERVED_WORDS = ["user"]


def clean_columns(column_names: typing.Iterable) -> typing.List[str]:
    cleaned_names = []
    for column in column_names:
        if column in RESERVED_WORDS:
            cleaned_names.append(f'"{column}"')
        else:
            cleaned_names.append(column)
    return cleaned_names


class SqlClient:
    def __init__(self, pool: asyncpg.pool.Pool, bot: "Iceteabot" = None, ):
        self.bot: typing.Optional["Iceteabot"] = bot
        self.pool = pool
        self.generator = generator(1, 1)

    async def add_user(self, user: int) -> models.User:
        new_user = models.User(self, user)
        await self.execute("INSERT INTO users (id) VALUES ($1) ON CONFLICT (id) do nothing;", user)
        return new_user

    async def add_users(self, users: typing.List[typing.Union[discord.User, discord.Member, int]]):
        return await self.execute_many("INSERT INTO users (id) VALUES ($1) on conflict (id) do nothing;",
                                       [(getattr(user, "id", user),) for user in users])

    async def execute(self, query: str, *args) -> str:
        connection: asyncpg.Connection = await self.pool.acquire()
        try:
            response = await connection.execute(query, *args)
            return response
        finally:
            await self.pool.release(connection)

    async def execute_many(self, query: str, args: typing.List):
        connection: asyncpg.Connection = await self.pool.acquire()
        try:
            response = await connection.executemany(query, args)
            return response
        finally:
            await self.pool.release(connection)

    async def get(self, query, *args) -> asyncpg.Record:
        connection: asyncpg.Connection = await self.pool.acquire()
        try:
            response: asyncpg.Record = await connection.fetchrow(query, *args)
            return response
        finally:
            await self.pool.release(connection)

    async def get_model(self, model: "models.Model()", query: str, *args) -> typing.Any:
        connection: asyncpg.Connection = await self.pool.acquire()
        try:
            response: asyncpg.Record = await connection.fetchrow(query, *args)
            if response:
                model_fields = model.get_fields()
                return model(client=self, **{field.name: response.get(field.name) for field in model_fields})
        finally:
            await self.pool.release(connection)

    async def get_all(self, model: "models.Model()", query: str, *args) -> typing.AsyncGenerator:
        connection: asyncpg.Connection = await self.pool.acquire()
        try:
            async with connection.transaction():
                async for record in connection.cursor(query, *args):
                    yield model(client=self, **dict(record))
        finally:
            await self.pool.release(connection)

    async def raw_get_all(self, query: str, *args) -> typing.List[asyncpg.Record]:
        connection: asyncpg.Connection = await self.pool.acquire()
        try:
            return await connection.fetch(query, *args)
        finally:
            await self.pool.release(connection)

    async def fetch(self, query: str, *args) -> asyncpg.Record:
        async with self.pool.acquire() as connection:
            response: asyncpg.Record = await connection.fetchrow(query, *args)
            return response

    async def get_user(self, pid: int) -> models.User:
        async with self.pool.acquire() as connection:
            response = await connection.fetchrow("SELECT * FROM users where id = $1", pid)
            if response:
                return models.User(client=self, **dict(response))

    async def get_guild(self, pid: int) -> models.Guild:
        async with self.pool.acquire() as connection:
            response = await connection.fetchrow("SELECT * FROM guilds where id = $1", pid)
            if response:
                guild = models.Guild(client=self, **dict(response))
                await guild.get_data()
                return guild

    async def get_all_guilds(self) -> typing.List[models.Guild]:
        guilds = []
        async for guild in self.get_all(models.Guild, "SELECT * FROM guilds"):
            await guild.get_data()
            guilds.append(guild)
        return guilds

    async def update(self, model: models.Model):
        model_table = models.tables[type(model)]
        model_data = model.data
        model_primary_keys = ','.join(model.PRIMARY_KEY)
        insert_arguments = ','.join(f'${index}' for index in range(1, len(model_data) + 1))
        cleaned_column_names = clean_columns(list(model_data.keys())[1:])
        update_arguments = ','.join(
            f'{column} = excluded.{column}' for column in
            cleaned_column_names)
        connection: asyncpg.Connection = await self.pool.acquire()
        query = f'INSERT INTO {model_table} VALUES({insert_arguments}) ' \
            f'ON CONFLICT ({model_primary_keys}) DO UPDATE set {update_arguments};'
        try:
            await connection.execute(query,
                                     *model_data.values())
        finally:
            await self.pool.release(connection)

    async def delete(self, model: models.Model):
        model_table = models.tables[type(model)]
        # noinspection SqlResolve
        query = f"DELETE FROM {model_table} WHERE id = $1"
        await self.execute(query, model.id)

    async def delete_all(self, models_to_delete: typing.List[models.Model]):
        pass

    async def setup(self):
        async with self.pool.acquire() as connection:
            for table in models.tables.keys():
                table: models.Model = table
                try:
                    await connection.execute(table.setup_table())
                except asyncpg.DuplicateTableError:
                    continue
                except Exception as e:
                    print(f"failed to make table {table}")
                    raise e

    async def get_command_stats_overall(self) -> dict:
        response = {}
        top_commands = await self.raw_get_all("SELECT command,count(command) from commands "
                                              "group by command order by count(command) desc limit 5;")
        response['top_commands'] = {record['command']: record['count'] for record in top_commands}
        top_command_users = await self.raw_get_all("SELECT author,count(command) from commands "
                                                   "group by author order by count(command) desc limit 5")
        response['top_command_users'] = {record['author']: record['count'] for record in top_command_users}
        return response

    async def get_todays_stats(self) -> dict:
        response = {}
        top_commands_today = await self.raw_get_all(
            "SELECT command,count(command) from commands WHERE called::date = CURRENT_DATE "
            "group by command order by count(command) desc limit 5;")
        response['top_commands_today'] = {record['command']: record['count'] for record in top_commands_today}
        top_command_users_today = await self.raw_get_all(
            "SELECT author,count(author) from commands WHERE called::date = CURRENT_DATE "
            "group by author order by count(author) desc limit 5;")
        response['top_command_users_today'] = {record['author']: record['count'] for record in
                                               top_command_users_today}
        return response

    async def get_total_commands_used(self) -> int:
        data = await self.fetch("SELECT COUNT(*) FROM commands")
        return data.get("count", 0)

    async def get_total_commands_used_today(self) -> int:
        data = await self.fetch("SELECT COUNT(*) FROM commands where called::date = CURRENT_DATE")
        return data.get("count", 0)

    async def get_command_stats(self) -> "models.guild.CommandStats":
        response = {}
        response.update(await self.get_command_stats_overall())
        response.update(await self.get_todays_stats())
        response["total_commands_used"] = await self.get_total_commands_used()
        response["total_commands_used_today"] = await self.get_total_commands_used_today()
        return models.CommandStats(**response)

    async def get_todays_reminders(self):
        reminders = self.get_all(models.Reminder, "SELECT * FROM reminders WHERE delta::date = CURRENT_DATE")
        return [reminder async for reminder in reminders]

    async def delete_old_reminders(self):
        await self.execute("DELETE FROM reminders WHERE CURRENT_DATE > delta::date")

    async def update_member_last_spoke(self, mid: int, gid: int, timestamp: datetime.datetime):
        await self.execute(
            "INSERT INTO members (id,guild,last_spoke) VALUES ($1,$2,$3) "
            "ON CONFLICT(id,guild) do update set last_spoke = $3 WHERE members.guild = $2 "
            "AND members.id = $1;", mid, gid, timestamp)


if __name__ == '__main__':
    from utils.iceteabot import Iceteabot
