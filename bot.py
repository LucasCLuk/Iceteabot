import argparse
import asyncio
import os

from utils.iceteabot import Iceteabot

parser = argparse.ArgumentParser()
parser.add_argument("name", type=str, help="The name of the bot", default="iceteabot")
parser.add_argument("config", type=str, help="Path to config file for the bot", default="config.json")
args = parser.parse_args()


async def main():
    if os.path.exists(args.config):
        with open(args.config) as config_file:
            try:
                import ujson as json
            except ImportError:
                import json
            config = json.load(config_file)
    else:
        raise FileNotFoundError("Config file not found")
    bot = Iceteabot(config=config)
    bot.setup_logging()
    await bot.setup_database()
    await bot.start()


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
