import argparse
import asyncio

from utils.iceteabot import Iceteabot

parser = argparse.ArgumentParser()
parser.add_argument("--use-logging", type=bool, help="Path to log file for the bot", default=False,
                    required=False)
args = parser.parse_args()


async def main():
    bot = Iceteabot()
    if args.use_logging:
        bot.setup_logging()
    await bot.setup_database()
    await bot.start()


if __name__ == '__main__':
    asyncio.run(main())
