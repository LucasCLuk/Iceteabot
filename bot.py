import asyncio

import dotenv

from utils.iceteabot import Iceteabot


async def main():
    dotenv.load_dotenv()
    bot = Iceteabot()
    bot.setup_logging()
    await bot.setup_database()
    await bot.start()


if __name__ == '__main__':
    asyncio.run(main())
