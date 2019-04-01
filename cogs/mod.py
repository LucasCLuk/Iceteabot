from collections import Counter, defaultdict

import discord
from discord.ext import commands


class Mod(commands.Cog):
    """Moderation related commands."""

    def __init__(self, bot):
        self.bot = bot

        # _guild_id: set(user_id)
        self._recently_kicked = defaultdict(set)

    def __repr__(self):
        return '<cogs.Mod>'

    def __str__(self):
        return self.__class__.__name__

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send(error)
        elif isinstance(error, commands.CommandInvokeError):
            original = error.original
            if isinstance(original, discord.NotFound):
                await ctx.send(f'This entity does not exist: {original.text}')
            elif isinstance(original, discord.HTTPException):
                await ctx.send('Somehow, an unexpected error occurred. Try again later?')

    @staticmethod
    async def _basic_cleanup_strategy(ctx, search):
        count = 0
        async for msg in ctx.history(limit=search, before=ctx.message):
            if msg.author == ctx.me:
                await msg.delete()
                count += 1
        return {'Bot': count}

    @staticmethod
    async def _complex_cleanup_strategy(ctx, search):
        guild_data = await ctx.guild_data()
        prefixes = [key for key in guild_data.prefixes.keys()]

        def check(m):
            return m.author == ctx.me or any([m.content.startswith(prefix) for prefix in prefixes])

        deleted = await ctx.channel.purge(limit=search, check=check, before=ctx.message)
        return Counter(m.author.display_name for m in deleted)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def cleanup(self, ctx, search=100):
        """Cleans up the bot's messages from the channel.

        If a search number is specified, it searches that many messages to delete.
        If the bot has Manage Messages permissions then it will try to delete
        messages that look like they invoked the bot as well.

        After the cleanup is completed, the bot will send you a message with
        which people got their messages deleted and their count. This is useful
        to see which users are spammers.

        You must have Manage Messages permission to use this.
        """

        strategy = self._basic_cleanup_strategy
        if ctx.me.permissions_in(ctx.channel).manage_messages:
            strategy = self._complex_cleanup_strategy

        spammers = await strategy(ctx, search)
        deleted = sum(spammers.values())
        messages = [f'{deleted} message{" was" if deleted == 1 else "s were"} removed.']
        if deleted:
            messages.append('')
            spammers = sorted(spammers.items(), key=lambda t: t[1], reverse=True)
            messages.extend(f'- **{author}**: {count}' for author, count in spammers)

        await ctx.send('\n'.join(messages), delete_after=10)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, limit: int = 100):
        purged = await ctx.purge(limit)
        await ctx.send(f"Purged ${len(purged)} Messages")


def setup(bot):
    bot.add_cog(Mod(bot))
