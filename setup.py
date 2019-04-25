import argparse
import asyncio
import os

import asyncpg
import ujson

from database.sqlclient import SqlClient

parser = argparse.ArgumentParser()
parser.add_argument("config", type=str, help="Path to config file for the bot", default="config.json")
args = parser.parse_args()

if os.path.exists(args.config):
    with open(args.config) as config_file:
        config = ujson.load(config_file)
else:
    raise FileNotFoundError("Config file not found")


async def create_tables():
    pool = await asyncpg.create_pool(**config['database'])
    client = SqlClient(pool)
    await client.setup()


if __name__ == '__main__':
    asyncio.run(create_tables())
