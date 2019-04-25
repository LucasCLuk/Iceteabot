from discord.ext import commands

from utils.errors import BadTask
from utils.iceteacontext import IceTeaContext
from utils.paginator import TaskPaginator


class Tasks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_command_error(self, ctx, error):
        if isinstance(error, BadTask):
            await ctx.send("Invalid Task number or I cannot find said number")
        else:
            await ctx.send(str(error), delete_after=10)

    @commands.group(invoke_without_command=True)
    async def task(self, ctx: "IceTeaContext"):
        if ctx.invoked_subcommand is None:
            help_command = ctx.bot.get_command("help")
            await ctx.invoke(help_command, command="task")

    @task.command(aliases=['create', 'add'])
    async def new(self, ctx: "IceTeaContext", *, content: str):
        """Creates a new task for the user"""
        author_data = ctx.author_data
        await author_data.add_task(content)
        await ctx.send("Successfully added task")

    @task.group(invoke_without_command=True)
    async def view(self, ctx: "IceTeaContext", number: int = None):
        """Views all your tasks"""
        if number is None:
            help_command = ctx.bot.get_command("help")
            await ctx.invoke(help_command, command="task view")
        else:
            paginator = TaskPaginator(ctx, entries=await ctx.author_data.get_all_tasks())
            await paginator.paginate()

    @view.command()
    async def unfinished(self, ctx: "IceTeaContext"):
        all_tasks = await ctx.author_data.get_unfinished_tasks()
        if all_tasks:
            paginator = TaskPaginator(ctx, entries=all_tasks)
            await paginator.paginate()
        else:
            await ctx.send("You have no tasks")

    @view.command()
    async def finished(self, ctx: "IceTeaContext"):
        all_tasks = await ctx.author_data.get_finished_tasks()
        if all_tasks:
            paginator = TaskPaginator(ctx, entries=all_tasks)
            await paginator.paginate()
        else:
            await ctx.send("You have no tasks")

    @task.command()
    async def delete(self, ctx: "IceTeaContext", number: int):
        """Deletes a task by task number"""
        try:
            await ctx.author_data.delete_task(number)
            await ctx.send("Task successfully deleted")
        except BadTask as e:
            await ctx.send(e, delete_after=10)

    @task.command()
    async def finish(self, ctx: "IceTeaContext", number: int):
        """Marks a task as finished"""
        try:
            await ctx.author_data.finish_task(number)
            await ctx.send("Task successfully finished")
        except Exception as e:
            await ctx.send("No task with that error found")


def setup(bot):
    bot.add_cog(Tasks(bot))
