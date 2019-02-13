from discord.ext import commands
import discord
from utils import form_manager

class Form:

    @commands.command()
    async def startform(self, ctx):
        questions = [form_manager.Question("How do you do today?", key="hello0"),
                     form_manager.Question("How do you do Tomorrow?", key="hello1"),
                     form_manager.Question("How were you yesterday?", key="hello2"),
                     form_manager.Question("How Old are you?", int, key="hello1"), ]
        manager = form_manager.FormManager(questions)
        response = await manager.ask(ctx)
        await ctx.send(f"You're responses are: {response}")


def setup(bot):
    bot.add_cog(Form())
