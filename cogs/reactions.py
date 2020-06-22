import asyncio

import discord
import typing

from discord.ext import commands
from discord.ext.commands import RoleConverter, MessageConverter

from utils.iceteacontext import IceTeaContext
import emoji


class ReactionRoles(commands.Cog):
    def __init__(self, bot):
        self.bot: "Iceteabot" = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        await self.update_member_roles(payload)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        await self.update_member_roles(payload, False)

    async def update_member_roles(self, payload: discord.RawReactionActionEvent, add_role: bool = True):
        guild_id = payload.guild_id
        if guild_id:
            guild = self.bot.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)
            if member.bot:
                return
            guild_data = self.bot.get_guild_data(guild_id)
            reaction_role = guild_data.get_reaction_role(payload.message_id, str(payload.emoji))
            if reaction_role:
                role = reaction_role.get_role()
                if add_role:
                    try:
                        await member.add_roles(role)
                    except discord.Forbidden:
                        pass
                else:
                    try:
                        await member.remove_roles(role)
                    except discord.Forbidden:
                        pass

    @commands.group(invoke_without_command=True)
    async def reaction(self, ctx: "IceTeaContext"):
        """
        Handles Reactions roles configuration of Iceteabot.
        """
        await ctx.send_help(ctx.command)

    @reaction.command(name="setup")
    async def setup_reactions(self, ctx: "IceTeaContext"):
        """
        Interactive setup for adding reactions
        """
        guild_data = ctx.guild_data
        reaction_roles = []
        main_message = await ctx.send(
            "Welcome to Iceteabot's Interactive Reaction Role setup,\n"
            "to start add all the reactions you'd like to **this** message then say __**finish**__\n"
            "You have **150 seconds** to add all the reactions you want. ")
        try:
            finish_response = await ctx.bot.wait_for("message", check=lambda
                finish_message: finish_message.author == ctx.author and finish_message.content.lower() == "finish",
                                                     timeout=150)
            try:
                await finish_response.delete()
            except discord.Forbidden:
                pass
            updated_message: discord.Message = await main_message.channel.fetch_message(main_message.id)
            reactions = updated_message.reactions
            for reaction in reactions:
                await main_message.edit(content=
                                        f"for emoji {reaction.emoji} which role do you want me to add? "
                                        f"You can type the name/id/mention of the role")
                try:
                    message = await ctx.bot.wait_for("message", check=lambda
                        role_message: role_message.channel == ctx.channel and role_message.author == ctx.author,
                                                     timeout=150)
                    try:
                        role = await RoleConverter().convert(ctx, message.content)
                        if role <= ctx.me.top_role:
                            reaction_roles.append((reaction, role))
                        else:
                            await ctx.send("That role is above my top role, as a result I cannot add/remove ppl to it.")
                        try:
                            await message.delete()
                        except:
                            pass
                        await main_message.edit(content=f"Successfully mapped {reaction} to {role}")
                        await asyncio.sleep(3)
                    except commands.BadArgument:
                        return await ctx.send("Could not find that role, failed")
                except asyncio.TimeoutError:
                    pass
            await main_message.edit(
                content="Now that I have all the reactions mapped to roles all "
                        "that's left is which message do you want this assigned "
                        "to enter the ID or jumplink of the message ")
            response = await ctx.bot.wait_for("message", check=lambda
                response_message: response_message.author == ctx.author and response_message.channel == ctx.channel)
            try:
                message_to_listen_to = await MessageConverter().convert(ctx, response.content)
                for reaction, role in reaction_roles:
                    await guild_data.add_role_reaction(ctx.author.id, message_to_listen_to.id, str(reaction.emoji),
                                                       role.id)
                    await message_to_listen_to.add_reaction(reaction.emoji)
                await ctx.send_success(
                    "Processed successfully. I will now listen to reactions on the specified message"
                )
                await main_message.delete(delay=2)
            except commands.BadArgument:
                pass
        except asyncio.TimeoutError:
            await ctx.send("You've failed to type finish in time.")

    @reaction.command(name="list")
    async def roles(self, ctx: "IceTeaContext", message: discord.Message):
        """
        Lists all the roles currently mapped to a given message
        """
        reaction_roles = filter(lambda rr: rr.message_id == message.id, ctx.guild_data.reaction_roles)
        embed = discord.Embed()

        def get_role_mention_or_name(reaction_role):
            role = reaction_role.get_role()
            if role:
                return role.mention
            else:
                return f"<@&{reaction_role.role}>"

        embed.description = "\n".join([
            f"{r.emoji} - {get_role_mention_or_name(r)}" for r in reaction_roles
        ])
        embed.add_field(name="\u200b", value=f"[Message]({message.jump_url})")
        await ctx.send(embed=embed)

    @reaction.command(name="add")
    async def add_role(self, ctx: "IceTeaContext", message: discord.Message, role: discord.Role,
                       *, reaction: typing.Union[discord.Emoji, str]):
        """
        Maps a Reaction to a role on the given message
        """
        if isinstance(reaction, str):
            reaction = emoji.emojize(reaction)
        await ctx.guild_data.add_role_reaction(ctx.author.id, message.id, reaction, role)
        await message.add_reaction(reaction)
        await ctx.send_success()

    @reaction.command(name="remove")
    async def remove_role(self, ctx: "IceTeaContext", message: discord.Message, *,
                          reaction: typing.Union[discord.Emoji, str]):
        """
        Removes a given reaction from the database and the message

        """
        if isinstance(reaction, str):
            reaction = emoji.emojize(reaction)
        await ctx.guild_data.remove_role_reaction(message.id, reaction)
        message_reaction: typing.Optional[discord.Reaction] = discord.utils.get(message.reactions, emoji=str(reaction))
        if message_reaction:
            await message_reaction.clear()
        await ctx.send_success()


def setup(bot):
    bot.add_cog(ReactionRoles(bot))


if __name__ == '__main__':
    from utils.iceteabot import Iceteabot
