import argparse
import asyncio
import os

from utils.iceteabot import Iceteabot

parser = argparse.ArgumentParser()
parser.add_argument("--name", type=str, help="The name of the bot", default="iceteabot", required=False)
parser.add_argument("--config", type=str, help="Path to config file for the bot", default="data/config.json",
                    required=False)
parser.add_argument("--use-logging", type=bool, help="Path to log file for the bot", default=False,
                    required=False)
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
    if args.use_logging:
        bot.setup_logging()
    await bot.setup_database()
    await bot.start()


if __name__ == '__main__':
    asyncio.run(main())
