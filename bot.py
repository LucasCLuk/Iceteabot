import argparse
import os
import ujson
import discord
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
    bot.run()