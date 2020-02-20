import datetime

import discord
import psutil
from discord.ext import commands

from database import models
from utils.iceteacontext import IceTeaContext


class Stats(commands.Cog):
    """Bot usage statistics."""

    def __init__(self, bot):
        self.bot: "Iceteabot" = bot
        self.process = psutil.Process()
        self.medals = ["\U0001f947", "\U0001F948", "\U0001F949", "\U0001f3c5", "\U0001f3c5"]

    @commands.Cog.listener()
    async def on_socket_response(self, msg):
        self.bot.socket_stats[msg.get('t')] += 1

    @commands.command(hidden=True)
    async def socketstats(self, ctx):
        delta = datetime.datetime.utcnow() - self.bot.uptime
        minutes = delta.total_seconds() / 60
        total = sum(self.bot.socket_stats.values())
        cpm = total / minutes
        embed = discord.Embed(title=f"{ctx.me.display_name}",
                              description=f"{total:,} socket events observed\n ({cpm:.2f}/minute)",
                              colour=discord.Colour.blue())
        for event, value in self.bot.socket_stats.most_common():
            if event is None:
                continue
            percent = round((value / total) * 100, 2)
            embed.add_field(name=event.lower().replace("_", " "), value=f"{value:,} **({percent}%)**")
        await ctx.send(embed=embed)

    def get_bot_uptime(self, time, *, brief=False):
        if time:
            now = datetime.datetime.utcnow()
            delta = now - time
            hours, remainder = divmod(int(delta.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            days, hours = divmod(hours, 24)

            if not brief:
                if days:
                    fmt = '{d} days, {h} hours, {m} minutes, and {s} seconds'
                else:
                    fmt = '{h} hours, {m} minutes, and {s} seconds'
            else:
                fmt = '{h}h {m}m {s}s'
                if days:
                    fmt = '{d}d ' + fmt

            return fmt.format(d=days, h=hours, m=minutes, s=seconds)
        else:
            return None

    @commands.command()
    async def uptime(self, ctx):
        """Tells you how long the bot has been up for."""
        await ctx.send(f'Uptime: **{self.get_bot_uptime(self.bot.uptime)}**\nThe Last time I was reconnected was: '
                       f'**{self.get_bot_uptime(self.bot.last_reconnect)}** ')

    @commands.command(name="ram")
    async def ramusage(self, ctx):
        """Displays the bot's current ram usage"""
        memory_usage = psutil.Process().memory_full_info().uss / 1024 ** 2
        await ctx.send(f"{memory_usage:.2f} MiB")

    @commands.command(aliases=['botinfo', 'info'])
    @commands.guild_only()
    async def about(self, ctx: IceTeaContext):
        """Tells you information about the bot itself."""
        embed = discord.Embed(description=f"{ctx.bot.name} version **{ctx.bot.version}**")
        embed.colour = ctx.me.top_role.color
        owner = ctx.bot.owners[1]
        embed.set_thumbnail(url=ctx.me.avatar_url)
        guild_commands_used = f"{await ctx.guild_data.get_total_commands_used():,}"
        total_commands_used = f"{await ctx.bot.sql.get_total_commands_used():,}"
        embed.set_author(name=str(owner), icon_url=owner.avatar_url)
        guild_prefixes = list(ctx.guild_data.prefixes.keys())
        guild_prefixes.append(ctx.me.mention)
        # statistics
        total_members = sum(len(s.members) for s in ctx.bot.guilds)
        total_online = sum(1 for m in ctx.bot.get_all_members() if m.status != discord.Status.offline)
        unique_members = set(ctx.bot.get_all_members())
        unique_online = sum(1 for m in unique_members if m.status != discord.Status.offline)
        text = sum([len(guild.text_channels) for guild in ctx.bot.guilds])
        voice = sum([len(guild.voice_channels) for guild in ctx.bot.guilds])

        members = f"{total_members:,} total\n{total_online:,} online\n{len(unique_members):,} " \
            f"unique\n{unique_online:,} unique online"
        embed.add_field(name='Members', value=members)
        embed.add_field(name='Channels', value=f'{text + voice:,} total\n{text:,} text\n{voice:,} Voice')
        embed.add_field(name='Uptime', value=self.get_bot_uptime(self.bot.uptime, brief=True))
        embed.set_footer(text='Made with discord.py version {0}'.format(discord.__version__),
                         icon_url='http://i.imgur.com/5BFecvA.png')
        embed.timestamp = self.bot.uptime

        embed.add_field(name='Servers', value=str(len(self.bot.guilds)))
        embed.add_field(name='Commands Run', value=f"**Guild**: {guild_commands_used}\n" +
                                                   f"**Total**: {total_commands_used}")

        memory_usage = psutil.Process().memory_full_info().uss / 1024 ** 2
        cpu_usage = self.process.cpu_percent() / psutil.cpu_count()
        embed.add_field(name='Process', value=f'{memory_usage:.2f} MiB\n{cpu_usage:.2f}% CPU')
        embed.add_field(name="Guild Prefixes", value="\n".join(prefix for prefix in guild_prefixes))
        await ctx.send(embed=embed)

    @commands.command()
    async def invite(self, ctx: "IceTeaContext"):
        """Grabs the bot's invite link to share"""
        bot_invite_link = discord.utils.oauth_url(ctx.bot.client_id)
        await ctx.send(f"Invite Link: <{bot_invite_link}>")

    @staticmethod
    def _get_user(ctx: "IceTeaContext", user_id: int) -> str:
        member = ctx.guild.get_member(user_id)
        if member:
            return member.mention
        else:
            return f"<@{user_id}>"

    def command_stats_embed_builder(self, ctx, command_stats: models.CommandStats,
                                    title: str) -> discord.Embed:
        embed = discord.Embed(title=title)
        embed.colour = ctx.author.top_role.color
        embed.description = f"""{command_stats.total_commands_used} Commands Used\n
                                {command_stats.total_commands_used_today} Commands Used Today"""
        embed.add_field(name="Top Commands", value="\n".join(
            f"{self.medals[index]} : {command} ({usage:,} uses)" for index, (command, usage) in
            enumerate(command_stats.top_commands.items())))
        embed.add_field(name="Top Commands Today", value="\n".join(
            f"{self.medals[index]} : {command} ({usage:,} uses)" for index, (command, usage) in
            enumerate(command_stats.top_commands_today.items())))
        embed.add_field(name="Top Command Users", value="\n".join(
            f"{self.medals[index]} : {self._get_user(ctx, author)} ({usage:,} uses)" for index, (author, usage) in
            enumerate(command_stats.top_command_users.items())), inline=False)
        embed.add_field(name="Top Command Users Today", value="\n".join(
            f"{self.medals[index]} : {self._get_user(ctx, author)} ({usage:,} uses)" for index, (author, usage) in
            enumerate(command_stats.top_command_users_today.items())))
        return embed

    @commands.group(invoke_without_command=True)
    async def stats(self, ctx: "IceTeaContext"):
        """Display's command usage stats for the guild"""
        guild_data = ctx.guild_data
        command_stats = await guild_data.get_command_stats()
        embed = self.command_stats_embed_builder(ctx, command_stats, f"{ctx.guild.name} Command Usage Stats")
        await ctx.send(embed=embed)

    @stats.command(name="global")
    async def _global(self, ctx):
        command_stats = await ctx.bot.sql.get_command_stats()
        embed = self.command_stats_embed_builder(ctx, command_stats, f"Global Command Usage")
        await ctx.send(embed=embed)


def setup(bot: "Iceteabot"):
    bot.socket_stats.clear()
    bot.add_cog(Stats(bot))


if __name__ == '__main__':
    from utils.iceteabot import Iceteabot
