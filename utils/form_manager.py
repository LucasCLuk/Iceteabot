import asyncio
import typing

import discord
from discord.ext import commands


class Question:

    def __init__(self, question: str, response_data_type: typing.Type = str, key: str = None):
        # The string of the question being asked
        self.question = question
        self.response_data_type = response_data_type
        self.key = key or question

    def __eq__(self, other):
        return self.question == other.question

    def __str__(self):
        return self.question

    def validate(self, message: discord.Message):
        """Validates the answer given and converts it to the proper data type"""
        return self.response_data_type(message.content)


class FormManager:
    def __init__(self, questions: typing.List[Question], cancel_emoji: str = "\U0000274c",
                 timeout: int = None):
        self.questions = questions or []
        self.answers: typing.Dict[str, typing.Any] = {question.key: None for question in questions}
        self.cancel_emoji = cancel_emoji
        self.timeout = timeout
        self.message_cache: typing.List[discord.Message] = []

    async def ask(self, ctx: commands.Context) -> typing.Dict[str, typing.Any]:
        original_message: discord.Message = await ctx.send(f"Welcome to the form manager,"
                                                           f" if you wish to cancel or stop this form at any time, "
                                                           f"react to this message with {self.cancel_emoji}")
        await original_message.add_reaction(self.cancel_emoji)
        self.message_cache.append(original_message)
        question_index = 0
        while question_index < len(self.questions):
            if question_index >= len(self.questions):
                break
            question = self.questions[question_index]
            question_message = await ctx.send(str(question))
            self.message_cache.append(question_message)
            reaction_cancel = ctx.bot.wait_for("reaction_add",
                                               check=lambda reaction,
                                                            user: reaction.message.id == original_message.id
                                                                  and reaction.emoji == self.cancel_emoji and user == ctx.author)
            response = ctx.bot.wait_for("message",
                                        check=lambda message: message.author == ctx.author and question.validate(
                                            message), timeout=self.timeout)
            done, pending = await asyncio.wait([
                reaction_cancel,
                response
            ], return_when=asyncio.FIRST_COMPLETED)

            try:
                stuff = done.pop().result()
                if isinstance(stuff, discord.Message):
                    self.answers[question.key] = stuff.content
                    self.message_cache.append(response)
                    question_index += 1
                elif isinstance(stuff, tuple):
                    break
            except Exception as e:
                # if any of the tasks died for any reason,
                #  the exception will be replayed here.
                pass

            for future in pending:
                future.cancel()  # we don't need these anymore
        await ctx.send("Alright, the form has finished. I will now process the results.")
        try:
            if self.message_cache:
                await ctx.channel.delete_messages(self.message_cache)
        finally:
            return self.answers
