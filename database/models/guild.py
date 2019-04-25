import dataclasses
import datetime
import typing

import asyncpg
import discord
from sentry_sdk import capture_exception

from database.models.activity import Activity
from database.models.channel import Channel
from database.models.command_call import CommandCall
from database.models.faq import FAQ
from database.models.member import Member
from database.models.model import Model
from database.models.prefix import Prefix
from database.models.reminder import Reminder
from database.models.tag import Tag
from utils.errors import ActivityAlreadyExists


@dataclasses.dataclass()
class Guild(Model):
    welcome_channel: int = None
    welcome_message: str = None
    leaving_channel: int = None
    leaving_message: str = None
    tracking: bool = True
    premium: bool = False
    _blocked_channels: typing.Dict[int, "Channel"] = dataclasses.field(default_factory=dict, repr=False, compare=False)
    _prefixes: typing.Dict[str, "Prefix"] = dataclasses.field(default_factory=dict, repr=False, compare=False)
    _activities: typing.Dict[str, "Activity"] = dataclasses.field(default_factory=dict, repr=False, compare=False)
    _faqs: typing.Dict[str, "FAQ"] = dataclasses.field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def setup_table(cls) -> str:
        return 'CREATE TABLE IF NOT EXISTS guilds(' \
               'id bigint primary key ,' \
               'welcome_channel bigint,' \
               'welcome_message text,' \
               'leaving_channel bigint,' \
               'leaving_message text,' \
               'tracking boolean,' \
               'premium boolean);'

    @property
    def activities(self):
        return self._activities

    @activities.setter
    def activities(self, value):
        self._activities = value

    @property
    def prefixes(self) -> typing.Dict[str, "Prefix"]:
        return self._prefixes

    @prefixes.setter
    def prefixes(self, value):
        self._prefixes = value

    @property
    def faqs(self):
        return self._faqs

    @faqs.setter
    def faqs(self, value):
        self._faqs = value

    @property
    def activity_roles(self) -> typing.List[typing.Optional[discord.Role]]:
        return [activity.get_role() for activity in self._activities.values()]

    @property
    def blocked_channels(self):
        return self._blocked_channels

    async def add_member(self, mid):
        new_member = Member(self.client, mid, guild=self.id)
        connection: asyncpg.Connection = await self.client.pool.acquire()
        try:
            transaction: asyncpg.connection.transaction.Transaction = connection.transaction()
            await transaction.start()
            await connection.execute("INSERT INTO users (id) VALUES ($1) ON CONFLICT(id) do nothing;", mid)
            await connection.execute("INSERT INTO members (id,guild) VALUES ($1,$2) on conflict(id,guild) do nothing;",
                                     mid, self.id)
            await transaction.commit()
        except Exception as e:
            capture_exception(e)
        finally:
            await self.client.pool.release(connection)
        return new_member

    async def add_members(self, members: typing.List[int]):
        await self.client.execute_many("INSERT INTO members (id,guild) VALUES($1,$2) on conflict do nothing;",
                                       [(user, self.id) for user in members])

    async def remove_member(self, mid):
        await self.client.execute("DELETE FROM members where id = $1 and guild = $2", mid, self.id)

    async def remove_members(self, members: typing.List[int]):
        await self.client.execute_many("DELETE FROM members WHERE id = $1 and guild = $2;",
                                       [(user, self.id) for user in members])

    async def get_member(self, mid) -> "Member":
        member = await self.client.get_model(Member, "SELECT * FROM members "
                                                     "INNER JOIN users ON users.id = $1 and guild = $2 "
                                                     "WHERE members.id = $1 AND guild = $2;",
                                             mid, self.id)
        return member

    async def get_all_members(self, gid) -> typing.AsyncGenerator[None, "Member"]:
        members = self.client.get_all(Member,
                                      "SELECT * FROM members "
                                      "INNER JOIN users ON (users.id = members.id) WHERE guild = $1",
                                      gid)
        return members

    async def add_member_nickname(self, mid: int, nickname: str):
        connection: asyncpg.Connection = await self.client.pool.acquire()
        try:
            transaction: asyncpg.connection.transaction.Transaction = connection.transaction()
            await transaction.start()
            await connection.execute("INSERT INTO users (id) VALUES ($1) ON CONFLICT(id) do nothing;", mid)
            await connection.execute("INSERT INTO members (id,guild) VALUES ($1,$2) on conflict do nothing;", mid,
                                     self.id)
            await connection.execute(
                "INSERT INTO nicknames (id, member, nickname, changed, guild) VALUES ($1,$2,$3,$4,$5)",
                next(self.client.generator), mid,
                nickname, datetime.datetime.utcnow(), self.id)
            await transaction.commit()
        except Exception as e:
            capture_exception(e)
        finally:
            await self.client.pool.release(connection)

    async def find_tag_by_id(self, tid) -> typing.Optional["Tag"]:
        return await self.client.get_model(Tag, "SELECT * FROM tags where id = $1", tid)

    async def get_tag(self, title: str) -> typing.Optional["Tag"]:
        tag = await self.client.get_model(Tag,
                                          'SELECT t.title <> tags.title AS "alias", t.count, tags.* '
                                          'FROM tags INNER JOIN tagslink t on tags.id = t.tag '
                                          'WHERE t.guild = $1 and t.title = $2',
                                          self.id, title)
        return tag

    async def get_all_tags(self) -> typing.List["Tag"]:
        return [tag async for tag in self.client.get_all(Tag, "SELECT * FROM tags WHERE guild = $1", self.id)]

    async def get_member_tags(self, author: int) -> typing.List["Tag"]:
        tags = self.client.get_all(Tag, 'SELECT * FROM tags where author = $1 and guild = $2', author, self.id)
        return [tag async for tag in tags]

    async def get_member_top_tags(self, author: int) -> typing.List["Tag"]:
        return [tag async for tag in self.client.get_all(Tag,
                                                         "SELECT * FROM tagslink where author = $1 and guild = $2 "
                                                         "ORDER BY count DESC LIMIT 5",
                                                         author, self.id)]

    async def get_tag_stats(self) -> typing.Tuple[int, int]:
        response = await self.client.get('SELECT SUM(count),COUNT(id) FROM tagslink WHERE guild = $1', self.id)
        return response['sum'], response['count']

    async def get_top_tag_users(self) -> typing.List[asyncpg.Record]:
        users = await self.client.raw_get_all(
            "SELECT author, COUNT(author) FROM tagcalls WHERE guild = $1 ORDER BY COUNT(author) DESC LIMIT 5", self.id)
        return users

    async def get_top_tags(self):
        return [tag async for tag in
                self.client.get_all(Tag, "SELECT * FROM tagslink "
                                         "where guild = $1 ORDER BY count DESC LIMIT  5", self.id)]

    async def get_top_tag_creators(self) -> typing.List[asyncpg.Record]:
        return await self.client.raw_get_all(
            "SELECT author,Count(author) FROM tags WHERE guild = $1 ORDER BY Count(author) DESC  LIMIT 5", self.id)

    async def get_member_tag_count(self, mid: int):
        return await self.client.get(
            "SELECT COUNT(author), SUM(count) FROM tagslink WHERE guild = $1 and author = $2", self.id, mid)

    async def get_all_aliases(self, tag: typing.Union["Tag", int]) -> typing.List["Tag"]:
        tag_id = getattr(tag, "id", tag)
        response = self.client.get_all(Tag, 'SELECT * FROM tagslink WHERE tag = $1', tag_id)
        return [alias async for alias in response]

    async def create_tag(self, title: str, content: str, author: int):
        tag_id = next(self.client.generator)
        tag_link_id = next(self.client.generator)
        query = 'WITH tag_insert AS ' \
                '(INSERT INTO tags (id, author, title, content, created, last_edited, guild) ' \
                'VALUES ($1,$2,$3,$4,$5,NULL,$6) RETURNING id) ' \
                'INSERT INTO tagslink (id, title, guild, tag,author,count) VALUES ($7,$3,$6,$1,$2,0);'
        connection: asyncpg.Connection = await self.client.pool.acquire()
        transaction: asyncpg.connection.transaction.Transaction = connection.transaction()
        await transaction.start()
        try:
            await connection.execute(query, tag_id, author, title.lower(), content, datetime.datetime.utcnow(), self.id,
                                     tag_link_id)
            await transaction.commit()
        except asyncpg.UniqueViolationError as e:
            await transaction.rollback()
            raise e
        except Exception as e:
            await transaction.rollback()
            raise e
        finally:
            await self.client.pool.release(connection)

    async def create_alias(self, original: str, new_alias: str, author: int):
        snowflake = next(self.client.generator)
        query = 'INSERT INTO tagslink (id, title,author, guild,count, tag) ' \
                'SELECT $1,$4,$5,0, tagslink.guild,tagslink.tag FROM tagslink ' \
                'WHERE tagslink.guild = $3 AND LOWER(tagslink.title)=$2; '
        await self.client.execute(query, snowflake, original, self.id, new_alias, author)

    async def call_tag(self, request: str, channel: int, author: int):
        connection: asyncpg.Connection = await self.client.pool.acquire()
        try:
            transaction: asyncpg.connection.transaction.Transaction = connection.transaction()
            await transaction.start()
            await connection.execute("UPDATE tagslink set count = count + 1 WHERE guild = $1 AND title = $2",
                                     self.id, request)
            tag = await connection.fetchrow("SELECT t.content FROM tagslink "
                                            "INNER JOIN tags t on tagslink.tag = t.id WHERE tagslink.title = $1",
                                            request.lower())
            tag_id = await connection.fetchrow("SELECT tagslink.id FROM tagslink WHERE tagslink.title = $1",
                                               request.lower())
            await connection.execute(
                "INSERT INTO tagcalls (id,tag_id, author, channel, guild, called) VALUES (DEFAULT,$1,$2,$3,$4,$5)",
                tag_id['id'], author, channel, self.id, datetime.datetime.utcnow())
            if tag:
                await transaction.commit()
                return tag['content']
            else:
                await transaction.rollback()
        except Exception as e:
            capture_exception(e)
        finally:
            await self.client.pool.release(connection)

    async def search_tags(self, query: str) -> typing.List["Tag"]:
        return [tag async for tag in self.client.get_all(Tag,
                                                         "SELECT title FROM tags WHERE guild = $1 "
                                                         "and levenshtein(title,$2) <= 3 "
                                                         "ORDER BY levenshtein(title,$2) DESC LIMIT 5",
                                                         self.id, query)]

    async def get_random_tag(self) -> typing.Optional["Tag"]:
        return await self.client.get_model(Tag,
                                           "SELECT title,content FROM tags WHERE guild = $1"
                                           " OFFSET FLOOR(RANDOM() * (SELECT COUNT(*) "
                                           "FROM tags where guild = $1)) LIMIT 1",
                                           self.id)

    async def call_command(self, ctx):
        command_call = CommandCall(self.client, author=ctx.author.id, called=ctx.message.created_at,
                                   command=ctx.command.qualified_name, guild=self.id)
        await command_call.save()

    async def add_activity(self, name, role):
        new_activity = self.activities.get(name.lower())
        if not new_activity:
            new_activity = Activity(client=self.client, guild=self.id, status=name.lower(), role=role)
            await new_activity.save()
            return new_activity
        else:
            raise ActivityAlreadyExists

    async def remove_activity(self, name: str):
        activity = self._activities.pop(name)
        await activity.delete()
        del activity

    async def block_channel(self, channel: int, author: int, reason: str = None):
        block = Channel(client=self.client, guild=self.id, blocker=author, reason=reason)
        response = await block.save()
        if response:
            self._blocked_channels[channel] = block
            return block

    async def unblock_channel(self, channel):
        block = self.blocked_channels.get(channel)
        if block is not None:
            response = await block.delete()
            if response:
                del self.blocked_channels[channel]
                return block

    async def add_faq(self, ctx, question: str, answer: str) -> typing.Optional["FAQ"]:
        new_faq = FAQ(guild=self.id, author=ctx.author.id, question=question, answer=answer, client=self.client)
        response = await new_faq.save()
        if response:
            return new_faq

    async def load_faqs(self):
        faqs = self.client.get_all(FAQ, "SELECT * FROM faqs WHERE guild = $1", self.id)
        self._faqs = {faq.id: faq async for faq in faqs}

    async def load_prefixes(self):
        prefixes = self.client.get_all(Prefix, "SELECT * FROM prefixes WHERE guild = $1",
                                       self.id)
        self._prefixes.update({str(prefix): prefix async for prefix in prefixes})

    async def load_activities(self):
        activities = self.client.get_all(Activity, "SELECT * FROM activities WHERE guild = $1", self.id)
        self._activities.update({activity.id: activity async for activity in activities})

    async def load_blocked_channels(self):
        blocked_channels = self.client.get_all(Channel, "SELECT * FROM channels WHERE guild = $1", self.id)
        self._blocked_channels = {channel.id: channel async for channel in blocked_channels}

    async def get_data(self):
        await self.load_prefixes()
        await self.load_faqs()
        await self.load_activities()
        await self.load_blocked_channels()

    async def add_prefix(self, prefix: str, author: int):
        new_prefix = Prefix(guild=self.id, author=author, prefix=prefix, client=self.client)
        await new_prefix.save()
        self._prefixes[prefix] = new_prefix
        return new_prefix

    async def delete_prefix(self, prefix) -> typing.Optional["Prefix"]:
        selected = self._prefixes.pop(prefix, None)
        if selected is not None:
            await selected.delete()
            return selected

    async def get_member_reminders(self, mid: int, cid: int) -> typing.List["Reminder"]:
        reminders = self.client.get_all(Reminder,
                                        'SELECT * FROM reminders where "user" = $1 and channel = $2 ORDER BY delta '
                                        'limit 10',
                                        mid,
                                        cid)
        return [reminder async for reminder in reminders]

    async def get_command_stats_overall(self) -> dict:
        response = {}
        top_commands = await self.client.raw_get_all("SELECT command,count(command) from commands "
                                                     "WHERE guild = $1 "
                                                     "group by command order by count(command) desc limit 5;", self.id)
        response['top_commands'] = {record['command']: record['count'] for record in top_commands}
        top_command_users = await self.client.raw_get_all("SELECT author,count(command) from commands WHERE "
                                                          "guild = $1 "
                                                          "group by author order by count(command) desc limit 5;",
                                                          self.id)
        response['top_command_users'] = {record['author']: record['count'] for record in top_command_users}
        return response

    async def get_todays_stats(self) -> dict:
        response = {}
        top_commands_today = await self.client.raw_get_all("SELECT command,count(command) from "
                                                           "commands WHERE guild = $1 "
                                                           "and called::date = CURRENT_DATE "
                                                           "group by command order by count(command) desc limit 5;",
                                                           self.id)
        response['top_commands_today'] = {record['command']: record['count'] for record in top_commands_today}
        top_command_users_today = await self.client.raw_get_all("SELECT author,count(author) from "
                                                                "commands WHERE guild = $1 "
                                                                "and called::date = CURRENT_DATE "
                                                                "group by author order by count(author) desc limit 5;",
                                                                self.id)
        response['top_command_users_today'] = {record['author']: record['count'] for record in
                                               top_command_users_today}
        return response

    async def get_total_commands_used(self) -> int:
        data = await self.client.fetch("SELECT COUNT(*) FROM commands WHERE guild = $1", self.id)
        return data.get("count", 0)

    async def get_total_commands_used_today(self) -> int:
        data = await self.client.fetch("SELECT COUNT(*) FROM commands WHERE guild = $1 and called::date = CURRENT_DATE",
                                       self.id)
        return data.get("count", 0)

    async def get_command_stats(self) -> "CommandStats":
        response = {}
        response.update(await self.get_command_stats_overall())
        response.update(await self.get_todays_stats())
        response["total_commands_used"] = await self.get_total_commands_used()
        response["total_commands_used_today"] = await self.get_total_commands_used_today()
        return CommandStats(**response)


@dataclasses.dataclass()
class CommandStats:
    top_commands: dict = dataclasses.field(default_factory=dict)
    top_command_users: dict = dataclasses.field(default_factory=dict)
    top_commands_today: dict = dataclasses.field(default_factory=dict)
    top_command_users_today: dict = dataclasses.field(default_factory=dict)
    total_commands_used: int = 0
    total_commands_used_today: int = 0
