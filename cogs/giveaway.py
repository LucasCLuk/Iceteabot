import random
import typing
from dataclasses import dataclass, field

import discord
from discord.ext import commands


@dataclass
class GiveawayEvent:
    owner: discord.Member
    message: discord.Message
    reactions: typing.Dict[str, typing.List[discord.Member]] = field(default_factory=dict)
    closed: bool = False
    winners: typing.List[discord.Member] = field(default_factory=list)

    def choose_winner(self, reaction: str = None) -> discord.Member:
        while True:
            if reaction in self.reactions:
                winner = random.choice(self.reactions[reaction])
            else:
                users = []
                for reacted_users in self.reactions.values():
                    users += reacted_users
                winner = random.choice(set(users))
            if winner not in self.winners:
                break
            else:
                continue
        self.winners.append(winner)
        return winner

    async def close(self):
        updated_message = await self.message.channel.fetch_message(self.message.id)
        for reaction in updated_message.reactions:
            users = await reaction.users().flatten()
            self.reactions[str(reaction)] = users
        try:
            await updated_message.clear_reactions()
        except discord.Forbidden:
            pass
        await updated_message.channel.send(
            f"Giveaway closed,any reactions added now will no longer count.")


class Giveaway(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.giveaways: typing.Dict[discord.Guild, GiveawayEvent] = {}

    async def cog_check(self, ctx):
        return ctx.guild is not None

    @commands.command(aliases=["startgiveaway", 'startgw'])
    @commands.has_permissions(manage_messages=True)
    async def opengiveaway(self, ctx):
        """Opens a giveaway

        The bot will send a message and everyone who reacts to the message is entered. Each user can only enter once
        regardless of how many reactions they add. Only 1 giveaway can be running at a time per guild.

        """
        if ctx.guild not in self.giveaways:
            message = await ctx.send("**Giveaway open, everyone who reacts to this message with any reaction "
                                     "is entered, each user is only counted once**")
            self.giveaways[ctx.guild] = GiveawayEvent(ctx.author, message)
        elif ctx.author in self.giveaways[ctx.guild]:
            await ctx.send(
                "I can only hold 1 giveaway per person, end your current giveaway to start a new one")

    @commands.command(aliases=['stopgiveaway', 'stopgw'])
    @commands.has_permissions(manage_messages=True)
    async def closegiveaway(self, ctx):
        """Closes the giveaway, you can only close your own giveaways. This does used for preventing further entries"""
        if ctx.author in self.giveaways[ctx.guild]:
            await self.giveaways[ctx.guild].close()

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def giveawaychoose(self, ctx, reaction: str = None):
        """Chooses from the pool of entries and announces the winner. You can keep using this command,
        No person can win more than once per giveaway"""
        if ctx.author in self.giveaways[ctx.guild]:
            winner = self.giveaways[ctx.guild].choose_winner(reaction)
            await ctx.send(f"Congratulations: {winner.mention}!")


def setup(bot):
    bot.add_cog(Giveaway(bot))
