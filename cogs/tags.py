import asyncpg
import discord

from database import models
from database.sqlclient import SqlClient
from utils.errors import TagAlreadyExists, TagNotFound
from utils.iceteabot import Iceteabot
from utils.iceteacontext import IceTeaContext
from utils.paginator import TagPaginator
from utils.permissions import *


class TagConverter(commands.Converter):

    async def convert(self, ctx: "IceTeaContext", argument: str):
        tag = await ctx.guild_data.get_tag(argument)
        if tag is None:
            raise TagNotFound(argument)
        else:
            return tag


# noinspection PyTypeChecker
class Tags(commands.Cog):
    def __init__(self, bot):
        self.bot: "Iceteabot" = bot
        self.sql: "SqlClient" = bot.sql
        self.medals = ["\U0001f947", "\U0001F948", "\U0001F949"]

    async def cog_check(self, ctx):
        return ctx.guild is not None

    async def cog_command_error(self, ctx, error):
        if isinstance(error, TagNotFound):
            # response_list = await self.search_tags(ctx, error.param)
            # if len(response_list) > 0:
            #     response_message = "\n".join([row.id for row in response_list])
            #     await ctx.send(f"Tag **{error.param}** not found\ninstead found these tags:\n\n{response_message}")
            await ctx.send(f"Tag ``{error.param}`` Not Found")
        elif isinstance(error, TagAlreadyExists):
            await ctx.send(f"``{error.param}`` already exists")
        else:
            await ctx.send(f"```\n{error}\n```", delete_after=20)

    async def guild_tag_stats(self, ctx: "IceTeaContext"):
        guild_tag_amount, guild_tag_uses = await ctx.guild_data.get_tag_stats()
        embed = discord.Embed(colour=discord.Colour.blurple(), title=f"{ctx.guild.name} Stats")
        embed.set_footer(text="These statistics are server-specific")
        embed.description = f"{guild_tag_amount} tags, {guild_tag_uses} Tag Uses"
        top_tags = await ctx.guild_data.get_top_tags()
        top_tag_users = {row['author']: row['count'] for row in await ctx.guild_data.get_top_tag_users()}
        top_tag_creators = {creator.id: creator for creator in await ctx.guild_data.get_top_tag_creators()}
        top_three_tags = ["{0} : {1} ({2} uses)".format(medal, tag, tag.count) for medal, tag in
                          zip(self.medals, top_tags)]
        top_three_users = [
            "{0} : {1} ({2} times)".format(medal, ctx.guild.get_member(int(user)).mention, top_tag_users[user]) for
            medal, user in zip(self.medals, top_tag_users)]
        top_three_creators = [
            "{0} : {1} ({2} tags)".format(medal, ctx.guild.get_member(int(user['author'])).mention,
                                          top_tag_creators[user['author']]) for
            medal, user in zip(self.medals, top_tag_creators)
        ]
        embed.add_field(name="Top Tags", value="\n".join(top_three_tags), inline=False)
        embed.add_field(name="Top Tag Users", value="\n".join(top_three_users), inline=False)
        embed.add_field(name="Top Tag Creators", value="\n".join(top_three_creators), inline=False)
        return await ctx.send(embed=embed)

    async def member_tag_stats(self, ctx: "IceTeaContext", member: discord.Member):
        tag_count = await ctx.guild_data.get_member_tag_count(member.id)
        member_top_tags = await ctx.guild_data.get_member_top_tags(member.id)
        guild_tag_amount, guild_tag_uses = await ctx.guild_data.get_tag_stats()
        embed = discord.Embed(colour=discord.Colour.blurple())
        embed.set_footer(text='These statistics are server-specific.')
        embed.set_author(name=member.display_name, icon_url=member.avatar_url)
        embed.add_field(name="Owned Tags", value=str(tag_count['count']))
        embed.add_field(name="Owned Tag Uses", value=str(tag_count['sum']))
        embed.add_field(name="Tag Command Uses", value=str(guild_tag_uses))
        for medal, tag in zip(self.medals, member_top_tags):
            embed.add_field(name=f"{medal} Owned Tag", value=f"{tag} ({tag.count} Uses)")
        return await ctx.send(embed=embed)

    @commands.group(invoke_without_command=True)
    async def tag(self, ctx: "IceTeaContext", *, tag_name: str):
        """Returns an existing tag"""
        tag_content = await ctx.guild_data.call_tag(tag_name, ctx.channel.id, ctx.author.id)
        if tag_content:
            await ctx.send(tag_content)
        else:
            await ctx.send("No Tag found")

    @tag.command(aliases=['add'])
    async def create(self, ctx: "IceTeaContext", name: str, *, content: str):
        """Creates a tag"""
        try:
            await ctx.guild_data.create_tag(name, await ctx.clean_content(content), ctx.author.id)
            await ctx.send(f"Tag {content} successfully created")
        except asyncpg.UniqueViolationError:
            await ctx.send("Tag Already Exists")
        except Exception as e:
            await ctx.send("Could not create Tag")
            ctx.dispatch_error(e)

    @tag.command()
    async def edit(self, ctx: "IceTeaContext", otag: TagConverter, *, new_content: str):
        """Edit a tag's content"""
        tag: models.Tag = otag
        if tag.alias:
            return await ctx.send("Unable to edit an alias")
        if tag.author == ctx.author.id:
            content = await ctx.clean_content(new_content)
            await tag.edit(content=content)
            await ctx.send("Tag updated Successfully")
        elif tag.author != ctx.author.id:
            await ctx.send("You do not own this tag")

    @tag.command()
    async def info(self, ctx: "IceTeaContext", *, otag: TagConverter):
        """Displays information on a specific tag"""
        tag: models.Tag = otag
        if not tag.alias:
            embed = discord.Embed(description=f"{ctx.message.guild.name} ``{tag.title}`` tag information")
            user = ctx.guild.get_member(tag.author)
            embed.set_author(name=user.display_name, icon_url=user.avatar_url)
            embed.add_field(name="Tag name", value=tag.title)
            embed.add_field(name="Amount used", value=str(tag.count))
            embed.timestamp = tag.created
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(description=f"{ctx.message.guild.name} ``{tag.title}`` alias information")
            user = ctx.guild.get_member(tag.author)
            embed.add_field(name="Author", value=user or "Unknown")
            embed.add_field(name="Amount used", value=str(tag.count))
            embed.timestamp = tag.created
            await ctx.send(embed=embed)

    @tag.command()
    async def delete(self, ctx: "IceTeaContext", *, otag: TagConverter):
        """Deletes a tag, only an administrator or tag owner may delete tags"""
        tag: models.Tag = otag
        if tag.alias:
            if ctx.author.guild_permissions.administrator or tag.author == ctx.author.id:
                try:
                    await tag.delete()
                    await ctx.send("aliases deleted")
                except:
                    await ctx.send("Alias unsuccessfully deleted")
        elif not tag.alias:
            if ctx.author.guild_permissions.administrator or tag.author == ctx.author.id:
                try:
                    await tag.delete()
                    await ctx.send("Tag and all aliases deleted")
                except:
                    await ctx.send("Tag unsuccessfully deleted")
        else:
            await ctx.send("No Tag with that name found")

    @tag.command()
    async def alias(self, ctx, name: str, *, new_alias: str):
        """Adds an alias to a tag, allows it to be called by other names"""
        try:
            await ctx.guild_data.create_alias(name, new_alias, ctx.author.id)
            await ctx.send("Alias successfully created")
        except:
            await ctx.send("Alias not created")

    @tag.command()
    async def stats(self, ctx, user: discord.Member = None):
        """Display either the servers's or the user's stats"""
        if user is None:
            await self.guild_tag_stats(ctx)
        else:
            await self.member_tag_stats(ctx, user)

    @tag.command()
    async def claim(self, ctx: "IceTeaContext", otag: TagConverter):
        """Claims an orphaned tag"""
        tag: models.Tag = otag
        author = ctx.guild.get_member(tag.author)
        if not author:
            tag.author = ctx.author.id
            await tag.save()
            await ctx.send(f"You have sucessfully claimed {tag.id}")
        else:
            await ctx.send("The Tag owner is still in the server")

    @tag.command()
    async def transfer(self, ctx, target: discord.Member, *, otag: TagConverter):
        """Allows a user to unclaim a tag, used for trading tags?"""
        tag: models.Tag = otag
        if tag.author == ctx.author.id:
            tag.author = target.id
            await tag.save()
            await ctx.send(f"You have sucessfully transferred this tag to {target}")
        else:
            await ctx.send("You do not own this tag")

    @tag.command()
    async def search(self, ctx: "IceTeaContext", *, query):
        """Searches for similar tags based on query

        eg: tag search dog

        found tags:
        dog
        dogs
        doggo

        """
        response_list = await ctx.guild_data.search_tags(query)
        if len(response_list) > 0:
            response_message = "\n".join([tag.title for tag in response_list])
            await ctx.send(f"Found these tags:\n{response_message}")
        else:
            await ctx.send("No similar tags found")

    @tag.command()
    async def random(self, ctx: "IceTeaContext"):
        """Retrieves a random tag from the database"""
        random_tag = await ctx.guild_data.get_random_tag()
        if random_tag is None:
            return await ctx.send("Unable to find any tags")
        await ctx.send(random_tag.content)

    @tag.command(name="list")
    async def _list(self, ctx: "IceTeaContext", target: discord.Member = None):
        """Display's a list of all tags owned by the mentioned user or if no one mentioned then authors"""
        target = target or ctx.author
        tags = await ctx.guild_data.get_member_tags(target.id)
        paginator = TagPaginator(ctx, entries=tags)
        await paginator.paginate()


def setup(bot):
    bot.add_cog(Tags(bot))
