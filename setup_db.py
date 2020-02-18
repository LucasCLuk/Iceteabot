import asyncio
import os

import asyncpg

from database.sqlclient import SqlClient


async def create_tables():
    pool = await asyncpg.create_pool(dsn=os.getenv('POSTGRES_URL'))
    client = SqlClient(pool)
    await client.setup()


if __name__ == '__main__':
    asyncio.run(create_tables())
