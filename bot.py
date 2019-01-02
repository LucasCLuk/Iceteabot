import ujson

from iceteabot import Iceteabot

with open("data/config.json") as config_file:
    config = ujson.load(config_file)

bot = Iceteabot(config=config)

if __name__ == '__main__':
    bot.run()
