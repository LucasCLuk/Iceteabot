import asyncio
import datetime
import random
import re
import typing

import discord
import lxml.etree
from discord.ext import commands, tasks
from discord.ext.commands import BucketType, UserInputError

from utils import formats
from utils.iceteacontext import IceTeaContext


class TimeParser:
    def __init__(self, argument):
        compiled = re.compile(r"(?:(?P<hours>\d+)h)?(?:(?P<minutes>\d+)m)?(?:(?P<seconds>\d+)s)?")
        self.original = argument
        try:
            self.seconds = int(argument)
        except ValueError as e:
            match = compiled.match(argument)
            if match is None or not match.group(0):
                raise commands.BadArgument('Failed to parse time.') from e

            self.seconds = 0
            hours = match.group('hours')
            if hours is not None:
                self.seconds += int(hours) * 3600
            minutes = match.group('minutes')
            if minutes is not None:
                self.seconds += int(minutes) * 60
            seconds = match.group('seconds')
            if seconds is not None:
                self.seconds += int(seconds)

        if self.seconds < 0:
            raise commands.BadArgument('I don\'t do negative time.')

        if self.seconds > 604800:  # 7 days
            raise commands.BadArgument('That\'s a bit too far in the future for me.')


async def memory_express_stock_checker(ctx, product_id):
    data = {}
    async with ctx.bot.aioconnection.get(f"https://www.memoryexpress.com/Products/{product_id}") as response:
        response.raise_for_status()
        tree = lxml.etree.fromstring(await response.text(), lxml.etree.HTMLParser())
        item_name = tree.xpath('//*[@id="ProductDetails"]/section[1]/header/h1/text()')
        try:
            item_price = tree.xpath('//*[@id="ProductPricing"]/div[4]/div[2]/div/text()')[1]
        except IndexError:
            try:
                item_price = tree.xpath('//*[@id="ProductPricing"]/div/div[2]/div')[1]
            except IndexError:
                item_price = "Unknown"
        inventory = tree.xpath('//*[@id="ProductDetailedInventory"]/div[2]')[0].xpath(
            '//*[@id="ProductDetailedInventory"]/div[2]/div/div[2]/div/div/ul')[0]
        for region in inventory:
            stores = []
            li = region.xpath("div[1]/text()")
            region_name = li[0]
            stores_tree = region.xpath("div[2]/ul")
            for store in stores_tree[0]:
                store_data = store.xpath("div")[0].xpath("span")
                store_name = store_data[0].xpath("text()")[0]
                store_quantity = store_data[2].xpath("text()")[0]
                stores.append((store_name, store_quantity))
            data[region_name] = stores
        online_store_div = tree.xpath('//*[@id="ProductDetailedInventory"]/div[2]/div/div[3]/div[2]/div[1]')[
            0].xpath(
            "span")
        online_store_name = online_store_div[0].xpath('text()')[0]
        online_store_stock = online_store_div[2].xpath('text()')[0]
        data[online_store_name] = [(online_store_name, online_store_stock)]
    return {"url": response.url, "item_price": item_price, "item_name": item_name[1], "data": data}


class StockWatcher:

    def __init__(self, ctx, product_id):
        self.ctx = ctx
        self.product_id = product_id
        self.product_found: bool = False

    async def item_in_stock(self) -> bool:
        data = await memory_express_stock_checker(self.ctx, self.product_id)
        item_name = data['item_name']
        item_url = data['url']
        edmonton_region = data['data']['Edmonton Region']
        for store in edmonton_region:
            stock = store[1]
            if stock != "Out of Stock":
                await self.ctx.send(f"{self.ctx.author.mention} - {item_name} is in stock: <{item_url}>")
                self.product_found = True
                break
        return self.product_found


class General(commands.Cog):
    def __init__(self, bot):
        self.bot: "Iceteabot" = bot
        self.memory_express_watchers: typing.Dict[discord.User, typing.Dict[str, StockWatcher]] = getattr(self.bot,
                                                                                                          "memory_express_watchers",
                                                                                                          {})
        self.stock_checker.start()

    def cog_unload(self):
        self.bot.memory_express_watchers = dict(self.memory_express_watchers)

    @commands.command(name="hug")
    async def hug(self, ctx, target: discord.Member = None):
        await ctx.send(f"Hello {target.mention if hasattr(target, 'mention') else ctx.author.mention}")

    @commands.command()
    async def flip(self, ctx: commands.Context):
        """Flips a coin"""
        coin = random.choice(["heads", "tails"])
        filepath = f"data/assets/{coin}.png"
        if coin == "heads":
            with open(filepath, "rb") as picture:
                await ctx.send(file=discord.File(fp=picture))
        elif coin == "tails":
            with open(filepath, "rb") as picture:
                await ctx.send(file=discord.File(fp=picture))

    @commands.command()
    async def roll(self, ctx, min: int = 0, max: int = 100):
        """Roll a number between two digits, if empty assumes 1-100"""
        await ctx.send("{0.message.author.mention} has rolled a {1}"
                       .format(ctx, random.randint(min, max)))

    @staticmethod
    async def say_permissions(ctx, member, channel):
        permissions = channel.permissions_for(member)
        entries = [(attr.replace('_', ' ').title(), val) for attr, val in permissions]
        await formats.entry_to_code(ctx, entries)

    @commands.command(name="permissions")
    @commands.guild_only()
    async def _permissions(self, ctx, *, member: discord.Member = None):
        """Shows a member's permissions.
        You cannot use this in private messages. If no member is given then
        the info returned will be yours.
        """
        channel = ctx.message.channel
        if member is None:
            member = ctx.message.author

        await self.say_permissions(ctx, member, channel)

    @commands.command()
    @commands.cooldown(20, 1)
    async def potato(self, ctx):
        """Displays a fancy potato gif"""
        myrandom = random.randint(0, 50)
        if myrandom < 25:
            with open("data/assets/potato.gif", "rb") as picture:
                await ctx.send(file=discord.File(fp=picture))
        elif myrandom > 25:
            with open("data/assets/bad_potato.gif", "rb") as picture:
                await ctx.send(file=discord.File(fp=picture))

    @commands.command()
    async def pick(self, ctx, choicea, choiceb):
        """Choose between 2 choices"""
        await ctx.send(random.choice([choicea, choiceb]))

    @commands.command()
    async def suggest(self, ctx, *, suggestion):
        """Adds a suggestion for a bot feature"""
        suggestion_channel = ctx.bot.get_channel(384410040880201730)
        if suggestion_channel is not None:
            embed = discord.Embed()
            embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
            embed.timestamp = ctx.message.created_at
            embed.description = suggestion
            embed.set_footer(text=ctx.bot.name)
            await suggestion_channel.send(embed=embed)
            await ctx.message.add_reaction("\U0001f44d")

    @commands.command(name="rps", enabled=False, hidden=True)
    async def rpsgame(self, ctx):
        choices = ['rock', 'paper', 'scissors']
        bot_choice = random.choice(choices)

        def check(m):
            return m.author == ctx.author and ctx.message.content.lower() in choices

        response = ctx.bot.wait_for("message", check=check)
        player_decision = choices.index(response.content.lower())

        if player_decision == bot_choice:
            await ctx.send("Its a TIE!")
        elif player_decision > bot_choice or player_decision:
            await ctx.send(f"{ctx.author} WINS!!!")

    @commands.group(invoke_without_command=True)
    @commands.cooldown(60, 1, BucketType.channel)
    async def faq(self, ctx, target: int = None):
        """Display's an embed with the top 20 faqs for the server. FAQs can be added via the subcommand add
        After using this command the user can type a number corresponding to that faq to get the detailed view about it.
        Optionally can provide a number right away to avoid waiting"""
        if len(ctx.guild_data.faqs) == 0:
            return await ctx.send("This guild has no FAQs")
        guild_faqs = sorted(ctx.guild_data.faqs.values(), key=lambda faq: faq.uses)
        try:
            if target is not None:
                target_faq = guild_faqs[target - 1]
                return await target_faq.call(ctx)
        except IndexError:
            return await ctx.send("No faq matching that number")
        embed = discord.Embed(title=f"{ctx.guild} FAQ")
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
        embed.description = "".join(
            [f":large_blue_diamond: **{index + 1}**. {question} - **({question.uses} Uses)** - ID: {question.id}" for
             index, question
             in
             enumerate(guild_faqs) if index <= 20])
        message = await ctx.send(embed=embed, content="Select a number")
        try:
            def check(m):
                try:
                    is_author = m.author == ctx.author
                    is_channel = m.channel == ctx.channel
                    is_digit = (int(m.content) - 1) < len(guild_faqs) and (int(m.content) - 1) < 20
                    return all([is_author, is_digit, is_channel])
                except ValueError:
                    return False

            response = await ctx.bot.wait_for("message", check=check, timeout=60)
            target_faq = guild_faqs[int(response.content) - 1]
            await target_faq.call(ctx)
        except asyncio.TimeoutError:
            await message.edit(embed=None, content="Ran out of time", delete_after=15)

    @faq.command()
    @commands.has_permissions(manage_guild=True)
    async def add(self, ctx: "IceTeaContext", *, question):
        """Registers a FAQ for this server, requires manage server permissions"""
        await ctx.send("Alright, now put the answer")
        try:
            answer = await ctx.bot.wait_for("message",
                                            check=lambda
                                                message: ctx.author == message.author and ctx.channel == message.channel,
                                            timeout=300)
            new_faq = await ctx.guild_data.add_faq(ctx, question, await ctx.clean_content(answer.content))
            if new_faq:
                await ctx.send("Successfully added Question to the FAQ")
            else:
                await ctx.send("Sorry, something went wrong during processing, please try again later", delete_after=15)
        except asyncio.TimeoutError:
            await ctx.send("Sorry, you took to long to answer.")

    @faq.command(name="delete")
    @commands.has_permissions(manage_guild=True)
    async def deletefaq(self, ctx, *, target):
        """Deletes a FAQ, can use the ID of the faq or the question itself"""
        try:
            await ctx.guild_data.delete_faq(target)
            await ctx.send("<a:thumpsup:445250162877661194>")
        except UserInputError as e:
            await ctx.send(e, delete_after=20)

    @commands.group(invoke_without_command=True)
    async def mem(self, ctx: IceTeaContext, *, product_id):
        try:
            data = await memory_express_stock_checker(ctx, product_id)
        except:
            return await ctx.send("Unable to Retriever information")
        item_price = data['item_price']
        url = data['url']
        item_name = data['item_name']
        embed = discord.Embed(description=f"Current Price: {item_price}")
        embed.set_author(name=item_name, url=url)
        for region, stores in data.items():
            embed.add_field(name=region, value="\n".join(f"{store} - {quantity}" for store, quantity in stores))
        await ctx.send(embed=embed)

    @mem.command()
    async def watch(self, ctx: IceTeaContext, *, product_id):
        self.memory_express_watchers[ctx.author] = {product_id: StockWatcher(ctx, product_id)}
        await ctx.send(
            f"Successfully added this item to my stock watcher, the next time I will check stock is in "
            f"{self.bot.get_time_difference(self.stock_checker.next_iteration.replace(tzinfo=None))}")

    @tasks.loop(hours=24)
    async def stock_checker(self):
        next_midnight = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0) + datetime.timedelta(days=1)
        self.stock_checker._next_iteration = next_midnight
        await discord.utils.sleep_until(next_midnight)
        users_to_be_removed = []
        for user in self.memory_express_watchers:
            watchers_items_to_be_removed = []
            for item_watched in self.memory_express_watchers[user].values():
                was_found = await item_watched.item_in_stock()
                if was_found:
                    watchers_items_to_be_removed.append(item_watched)
                    break
            if all(w.product_found for w in self.memory_express_watchers[user].values()):
                users_to_be_removed.append(user)
        for user in users_to_be_removed:
            self.memory_express_watchers.pop(user)

    @stock_checker.before_loop
    async def before_stock_checker(self):
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(General(bot))


if __name__ == '__main__':
    from utils.iceteabot import Iceteabot
