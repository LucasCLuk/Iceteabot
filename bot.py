import argparse
import asyncio
import os

import ujson

from utils.iceteabot import Iceteabot

parser = argparse.ArgumentParser()
parser.add_argument("name", type=str, help="The name of the bot", default="iceteabot")
parser.add_argument("config", type=str, help="Path to config file for the bot", default="config.json")
args = parser.parse_args()

if os.path.exists(args.config):
    with open(args.config) as config_file:
        config = ujson.load(config_file)
else:
    raise FileNotFoundError("Config file not found")

bot = Iceteabot(config=config)

if __name__ == '__main__':
    async def setup():
        bot.setup_logging()
        await bot.setup_database()
        await bot.start()


    asyncio.get_event_loop().run_until_complete(setup())
