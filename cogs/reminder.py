import asyncio
import typing

import discord
from discord.ext import commands

from database import models
from utils import time
from utils.iceteabot import Iceteabot
from utils.iceteacontext import IceTeaContext


class Reminder(commands.Cog):
    """Reminders to do something."""

    def __init__(self, bot):
        self.bot: "Iceteabot" = bot
        self.reminder_cache: typing.Dict[int, models.Reminder] = {}
        self.bot.loop.create_task(self._load_todays_reminders())
        self.task = self.bot.loop.create_task(self.reminder_task())

    def cog_unload(self):
        for reminder in self.reminder_cache.values():
            reminder.cancel()

    @commands.Cog.listener()
    async def on_reminder_complete(self, timer: models.Reminder):
        if timer.guild:
            channel = self.bot.get_channel(timer.channel)
            if channel is not None:
                author = channel.guild.get_member(timer.user)
                if all([channel, author]):
                    await channel.send(
                        f"{author.mention}, {timer.human_delta} you asked to be reminded of:\n{timer.message}")
        else:
            channel = self.bot.get_user(timer.user)
            if channel is not None:
                await channel.send(
                    f"{channel.mention}, {timer.human_delta} you asked to be reminded of:\n{timer.message}")
        await self.delete_reminder(timer.id)

    async def delete_reminder(self, rid):
        reminder = self.reminder_cache.pop(rid, None)
        if reminder:
            reminder.cancel()
            await reminder.delete()

    async def _load_todays_reminders(self):
        await self.bot.wait_until_ready()
        await self.bot.sql.delete_old_reminders()
        reminders = await self.bot.sql.get_todays_reminders()
        for reminder in reminders:
            reminder: models.Reminder
            if self.bot.get_channel(reminder.channel):
                if reminder.id not in self.reminder_cache:
                    self.reminder_cache[reminder.id] = reminder
                    await reminder.start()
            else:
                await reminder.delete()

    async def reminder_task(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            await self._load_todays_reminders()
            await asyncio.sleep(10800)

    async def create_reminder(self, ctx, when, event):
        """Creates a timer.
        Parameters
        -----------
        ctx : IceTeaContext
            The CTX of the command
        when: object
            When the timer should fire.
        event: str
            The event that will be dispatched on completion

        Note
        ------
        Arguments and keyword arguments must be JSON serializable.
        Returns
        --------
        :class:`Reminder`
        """
        reminder: models.Reminder = models.Reminder(ctx.bot.sql, ctx.message.id, user=ctx.author.id, message=when.arg,
                                                    time=ctx.message.created_at, delta=when.dt, event=event,
                                                    channel=ctx.channel.id,
                                                    guild=getattr(ctx.guild, "id", None))
        if (reminder.delta - reminder.time).total_seconds() > 600:
            await reminder.save()
        self.reminder_cache[reminder.id] = reminder
        await reminder.start()
        return reminder

    @commands.group(aliases=['timer', 'remind'], usage='<when>', invoke_without_command=True)
    async def reminder(self, ctx, *, when: time.UserFriendlyTime(commands.clean_content, default='something')):
        """Reminds you of something after a certain amount of time.
        The input can be any direct date (e.g. YYYY-MM-DD) or a human
        readable offset. Examples:
        - "next thursday at 3pm do something funny"
        - "do the dishes tomorrow"
        - "in 3 days do the thing"
        - "2d unmute someone"
        Times are in UTC.
        """

        data = await self.create_reminder(ctx, when, "reminder_complete")
        if data:
            delta = time.human_timedelta(when.dt, source=ctx.message.created_at)
            await ctx.send(f"Alright {ctx.author.mention}, I'll remind you about {when.arg} in {delta}.")

    @reminder.error
    async def reminder_error(self, ctx, error):
        if isinstance(error, (commands.BadArgument, commands.MissingRequiredArgument)):
            await ctx.send(str(error))

    @reminder.command(name="list")
    async def reminder_list(self, ctx: "IceTeaContext"):
        """Shows the user's 5 latest currently runny reminders that are within a day of expiring"""
        reminders = await ctx.guild_data.get_member_reminders(ctx.author.id, ctx.channel.id)
        embed = discord.Embed(colour=discord.Colour.blurple(), title="Reminders")
        for reminder in reminders:
            embed.add_field(name=f"In {time.human_timedelta(reminder.delta)} - ID: {reminder.id}",
                            value=reminder.message or "")
        await ctx.send(embed=embed)

    @reminder.command(name="delete")
    async def delreminder(self, ctx: "IceTeaContext", rid: int):
        """Deletes a reminder"""
        reminder = self.reminder_cache.pop(rid, await self.bot.sql.get_model(models.Reminder,
                                                                             "SELECT user FROM reminders where id = $1",
                                                                             rid))
        if reminder:
            if reminder.user == ctx.author.id:
                if reminder.task:
                    reminder.task.cancel()
                await reminder.delete()
                await ctx.send("Deleted", delete_after=10)
        else:
            await ctx.send("No Reminder found", delete_after=10)

    @reminder.command(name="active")
    @commands.is_owner()
    async def active_reminders(self, ctx: "IceTeaContext"):
        await ctx.send(f"There are currently **{len(self.reminder_cache)}** active reminders")


def setup(bot):
    bot.add_cog(Reminder(bot))
