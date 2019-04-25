import discord
import timeago
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType

from utils.iceteacontext import IceTeaContext


class Members(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        return ctx.guild

    @commands.command(aliases=["avatar"])
    @commands.cooldown(1, 30, type=BucketType.user)
    async def avatarurl(self, ctx: "IceTeaContext", target: discord.Member = None):
        """Displays the authors or target's avatar url"""
        if target is None:
            await ctx.send(f"{ctx.author.avatar_url}")
        else:
            await ctx.send(f"{target.avatar_url}")

    @commands.command(aliases=['uinfo'])
    async def userinfo(self, ctx: "IceTeaContext", target: discord.Member = None):
        """Display's a users information summary"""
        target = target or ctx.author
        target_data = await ctx.get_user_data(target)
        if target_data:
            nicknames = await target_data.get_nicknames()
        else:
            nicknames = []
        shared_servers = len([member for member in ctx.bot.get_all_members() if member == target])
        embed = discord.Embed(title=f"{target.nick or target.name} Profile")
        embed.set_author(name=f"{target.name} ({target.id})", icon_url=target.avatar_url)
        embed.set_thumbnail(url=target.avatar_url)
        embed.add_field(name="Shared Servers", value=f"{shared_servers} Shared")
        embed.add_field(name="Created",
                        value=f"""{timeago.format(target.created_at)} ({target.created_at.strftime("%b %d, %Y")})""")
        embed.add_field(name="Joined",
                        value=f"""{timeago.format(target.joined_at)} ({target.joined_at.strftime("%b %d, %Y")})""")
        embed.set_footer(text="Last Spoke In server")
        if target_data:
            embed.timestamp = target_data.last_spoke
        else:
            embed.timestamp = ctx.message.created_at
        if len(nicknames) > 0:
            embed.add_field(name="Nicknames", value=" , ".join(str(nick) for nick in nicknames[:5]), inline=False)
        embed.add_field(name="Roles", value=" , ".join([role.name for role in target.roles[:5] if len(role.name) > 0]),
                        inline=False)
        if target.activity:
            if isinstance(target.activity, discord.Spotify):
                embed.add_field(name="Currently Listening to",
                                value=f"**{target.activity.title}** by {target.activity.artist} ")
            else:
                embed.add_field(name="Currently Playing Since",
                                value=f"{target.activity.name}\n{target.activity.details}\n{target.activity.state}")
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Members(bot))
