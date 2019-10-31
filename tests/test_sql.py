import os

import asyncpg
import asynctest

from database import models
from database.sqlclient import SqlClient

database_settings = {
    "user": os.getenv("DATABASE_USER"),
    "password": os.getenv("DATABASE_PASSWORD"),
    "database": os.getenv("DATABASE_NAME"),
    'host': os.getenv("DATABASE_HOST"),
    "port": os.getenv("DATABASE_PORT"),
}


class TestGuildMethods(asynctest.TestCase):

    async def test_guild_methods(self):
        """Test Guild Methods"""
        pool = await asyncpg.create_pool(**database_settings)
        client = SqlClient(pool)
        await client.setup()
        # Creating the user
        user = models.User(client, 1234)
        await user.save()

        user_exists = await client.get_user(1234)
        self.assertIsNotNone(user_exists)

        guild = models.Guild(client, 12345)
        await guild.save()
        await guild.add_member(1234)

        member_exists = await guild.get_member(1234)
        self.assertIsNotNone(member_exists)

        new_prefix = await guild.add_prefix(">>", 1234)
        self.assertIn(new_prefix.prefix, guild.prefixes)

        await guild.delete_prefix(new_prefix.prefix)
        self.assertNotIn(new_prefix.prefix, guild.prefixes)

        await guild.delete()
        response = await client.get_guild(12345)
        self.assertIsNone(response)


class TestCommandStats(asynctest.TestCase):

    async def test_command_stats(self):
        pool = await asyncpg.create_pool(**database_settings)
        client = SqlClient(pool)
        await client.setup()
        guild = models.Guild(client, 12345)
        await guild.save()
        await guild.add_member(1234)
        for x in range(0, 10000):
            cmd = models.CommandCall(client, command="Help", guild=guild.id, author=1234)
            await cmd.save()
        data = await guild.get_command_stats()
        self.assertIsNotNone(data)

        global_data = await client.get_command_stats()
        self.assertIsNotNone(global_data)


class TagCRUDTests(asynctest.TestCase):

    async def test_tag_crud(self):
        pool = await asyncpg.create_pool(**database_settings)
        client = SqlClient(pool)
        await client.setup()
        guild = models.Guild(client, 12345)
        await guild.save()
        await guild.add_member(1234)
        try:
            await guild.create_tag("test1", "foobarbash", 1234)
        except asyncpg.UniqueViolationError:
            pass
        tag = await guild.get_tag("test1")
        self.assertIsNotNone(tag)
        await tag.delete()
        old_tag = await guild.get_tag("test1")
        self.assertIsNone(old_tag)


class TagAliasTest(asynctest.TestCase):

    async def test_alias(self):
        pool = await asyncpg.create_pool(**database_settings)
        client = SqlClient(pool)
        await client.setup()
        guild = await client.get_guild(12345)
        await guild.create_tag("test1", "Hello World", 1234)
        await guild.create_alias("test1", "fooalias", 1234)
        alias = await guild.get_tag("fooalias")
        self.assertIsNotNone(alias)
        await guild.call_tag("fooalias", 1111, 1234)


class CallTagTest(asynctest.TestCase):

    async def test_call_tag(self):
        pool = await asyncpg.create_pool(**database_settings)
        client = SqlClient(pool)
        await client.setup()
        guild = await client.get_guild(12345)
        await guild.call_tag("fooalias", 1111, 1234)
