import dotenv

from utils.iceteabot import Iceteabot

if __name__ == '__main__':
    dotenv.load_dotenv()
    bot = Iceteabot()
    bot.setup_logging()
    await bot.setup_database()
