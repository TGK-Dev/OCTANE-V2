import enum
import discord
import asyncio
import datetime
import re
from discord.ext import commands
from discord import app_commands
from utils.transformer import DMCConverter
from utils.converters import DMCConverter_Ctx
from discord.ext import tasks
from utils.db import Document
from typing import List
from copy import deepcopy


class Auctions_DB:
    def __init__(self, bot):
        self.db = bot.mongo["Auctions"]
        self.config = Document(self.db, "auctions_config")
        self.auctions = Document(self.db, "auctions")
        self.quque = Document(self.db, "auctions_queue")
        self.cach = {}
    
    async def create_config(self, guild_id:int):
        auction_data = {
            "_id": guild_id,
            "category": None,
            "request_channel": None,
            "queue_channel": None,
            "bid_channel": None,
            "payment_channel": None,
            "payout_channel": None,
            "log_channel": None,
            "manager_roles": [],
        }
        await self.config.insert(auction_data)
        return auction_data

    async def get_config(self, guild_id:int):
        if guild_id in self.cach.keys():
            return self.cach[guild_id]
        else:
            guild = await self.config.find(guild_id)
            if guild == None:
                guild = await self.create_config(guild_id)
            self.cach[guild_id] = guild
            return guild
    
    async def setup_config_cach(self):
        for guild in await self.config.get_all():
            if guild["_id"] not in self.cach.keys():
                self.cach[guild["_id"]] = guild
    



class Auction(commands.GroupCog, name="auction"):
    def __init__(self, bot):
        self.bot = bot
        self.bid_cache = {}
        self.bot.auction = Auctions_DB(bot)
        self.auction_loop_progress = False
        self.auction_task = self.auction_loop.start()

    async def item_autocomplete(self, interaction: discord.Interaction, string: str) -> List[app_commands.Choice[str]]:
        choices = []
        for item in self.bot.dank_items_cache.keys():
            if string.lower() in item.lower():
                choices.append(app_commands.Choice(name=item, value=item))
        if len(choices) == 0:
            return [
                app_commands.Choice(name=item, value=item)
                for item in self.bot.dank_items_cache.keys()
            ]
        else:
            return choices[:24]

    async def get_embed(self, data, first=True, winner:discord.Member=None):
        if winner:
            embed = discord.Embed(title=f"Auction for {data['quantity']}x{data['item']}", description="", color=self.bot.default_color)
            embed.description += f"**Starting Bid:** `⏣ {data['strating_price']:,}`\n"
            embed.description += f"**Bet Multiplier:** `⏣ {data['bet_multiplier']:,}`\n"  
            embed.description += f"**Bid Increment By:** `⏣ {data['current_bid']:,}`\n"
            embed.description += f"**Current Bid By:** {winner.mention}\n"
            embed.description += f"**Time Left:** `Auction Ended`\n"
            embed.description += f"**Auctioneer:** <@{data['auctioneer']}>\n"
            return embed
        
        if first:
            timestamp30s = int((datetime.datetime.now() + datetime.timedelta(seconds=30)).timestamp())
            embed = discord.Embed(title=f"Auction for {data['quantity']}x{data['item']}", description="", color=self.bot.default_color)
            embed.description += f"**Starting Bid:** `⏣ {data['strating_price']:,}`\n"
            embed.description += f"**Bet Multiplier:** `⏣ {data['bet_multiplier']:,}`\n"  
            embed.description += f"**Bid Increment By:** `None`\n"
            embed.description += f"**Current Bid By:** `None`\n"
            embed.description += f"**Time Left:** <t:{timestamp30s}:R>\n"
            embed.description += f"**Auctioneer:** <@{data['auctioneer']}>\n"
            return embed
        else:
            timestamp10s = int((datetime.datetime.now() + datetime.timedelta(seconds=10)).timestamp())
            embed = discord.Embed(title=f"Auction for {data['quantity']}x{data['item']}", description="", color=self.bot.default_color)
            embed.description += f"**Starting Bid:** `⏣ {data['strating_price']:,}`\n"
            embed.description += f"**Bet Multiplier:** `⏣ {data['bet_multiplier']:,}`\n"
            embed.description += f"**Bid Increment By:** `⏣ {data['current_bid']:,}`\n"
            embed.description += f"**Current Bidder:** <@{data['current_bid_by']}>\n"
            embed.description += f"**Time Left:** <t:{timestamp10s}:R>\n"
            embed.description += f"**Auctioneer:** <@{data['auctioneer']}>\n"
            return embed


    @tasks.loop(seconds=3)
    async def auction_loop(self):
        if self.auction_loop_progress:
            return
        self.auction_loop_progress = True
        data = self.bid_cache.copy()
        for auction in data:
            auction = self.bid_cache[auction]
            if auction['last_bid'] == None: continue
            if auction['last_bid'] + datetime.timedelta(seconds=auction['time_left']) < datetime.datetime.now():
                if auction['call_started'] == True: continue
                await auction['thread'].send(f"No Bet was place in last 10 seconds, starting closing calls")
                auction['call_started'] = True
                self.bot.dispatch("auction_calls", auction, 0, 10)
        self.auction_loop_progress = False

    @auction_loop.before_loop
    async def before_auction_loop(self):
        await self.bot.wait_until_ready()
    
    @commands.Cog.listener()
    async def on_auction_calls(self, data: dict, call_num:int, timeout:int):
        message: discord.Message = data['message']
        thread: discord.Thread = data['thread']
        if call_num == 0:
            embed = discord.Embed(description=f"# Going Once...", color=self.bot.default_color)
        if call_num == 1:
            embed = discord.Embed(description=f"# Going Twice...", color=self.bot.default_color)
        if call_num == 2:
            self.bot.dispatch("auction_end", data)
            return
        
        call_started_at = datetime.datetime.utcnow()
        time_passed = 0
        def check(m: discord.Message):
            if m.channel == thread:
                if m.author.id == data['auctioneer']: return False
                if m.author.id == data['current_bid_by']: return False
                if re.match('^[0-9]+', m.content):
                    return True              
        await thread.send(embed=embed)

        while True:
            try:
                timeout = 10 - time_passed
                if timeout <= 0: raise asyncio.TimeoutError
                msg = await self.bot.wait_for('message', check=check, timeout=timeout)
                ammout = await DMCConverter_Ctx().convert(msg, msg.content)
                if not ammout:
                    time_passed = int((datetime.datetime.utcnow() - call_started_at).total_seconds())
                    continue
                if ammout % data["bet_multiplier"] != 0:
                    time_passed = int((datetime.datetime.utcnow() - call_started_at).total_seconds())
                    await thread.send(f"Mininum Bid Increment is ⏣ {data['bet_multiplier']:,}")
                    continue
                if ammout >= 50000000000:
                    time_passed = int((datetime.datetime.utcnow() - call_started_at).total_seconds())
                    await thread.send("You can't bid more than ⏣ 50,000,000,000")
                    continue
                if msg.author.id == data['current_bid_by']:
                    time_passed = int((datetime.datetime.utcnow() - call_started_at).total_seconds())
                    await msg.reply("You are already the highest bidder")
                    continue
                if ammout > data["current_bid"]:
                    data['current_bid'] = ammout
                    data['current_bid_by'] = msg.author.id
                    data['time_left'] = 10
                    data['last_bid'] = datetime.datetime.now()
                    data['call_started'] = False
                    data['call_count'] = 0
                    self.bid_cache[data['message'].id] = data
                    await msg.reply(f"You have bid ⏣ {ammout:,} on {data['item']}")
                    embed = await self.get_embed(data)
                    await data['message'].edit(embed=embed)
                    return
            except asyncio.TimeoutError:
                data['call_count'] += 1
                self.bot.dispatch('auction_calls', data, data['call_count'], 10)
                return        
                
    
    @commands.Cog.listener()
    async def on_bet(self, message: discord.Message, data):
        ammount = await DMCConverter_Ctx().convert(message, message.content)
        if message.author.id == data['auctioneer']: 
            return await message.reply("You can't bid on your own auction")
        if ammount % data["bet_multiplier"] != 0:
            await message.reply(f"Mininum Bid Increment is ⏣ {data['bet_multiplier']:,}")
            return
        if ammount >= 50000000000:
            await message.reply("You can't bid more than ⏣ 50,000,000,000")
            return
        if message.author.id == data['current_bid_by']:
            await message.reply("You are already the highest bidder")
            return
        if ammount > data["current_bid"]:
            data['current_bid'] = ammount
            data['current_bid_by'] = message.author.id
            data['time_left'] = 10
            data['last_bid'] = datetime.datetime.now()
            await message.reply(f"You have bid ⏣ {ammount:,} on {data['item']}")
            embed = await self.get_embed(data, False)
            await data['message'].edit(embed=embed)
            await message.add_reaction("✅")
            self.bid_cache[data['_id']] = data
        elif ammount <= data["current_bid"]:
            await message.reply(f"You need to bid more than ⏣ {data['current_bid']:,}")
    
    @commands.Cog.listener()
    async def on_auction_end(self, data):
        try:
            del self.bid_cache[data['_id']]
        except:
            pass
        thread: discord.Thread = data['thread']
        message: discord.Message = data['message']
        await thread.send(embeds=[discord.Embed(description="# Going Thrice...", color=self.bot.default_color), discord.Embed(description=f"# Auction Ended Sold to <@{data['current_bid_by']}> for ⏣ {data['current_bid']:,}", color=0x00ff00)])
        await thread.edit(locked=True, name=f"{data['item']} Auction Ended")
        await message.reply(f"**Auction Ended**\n**Winner:** <@{data['current_bid_by']}>\n**Winning Bid:** ⏣ {data['current_bid']:,}")


    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.guild is None:
            return
        if not isinstance(message.channel, discord.Thread): return
        try:
            data = self.bid_cache[message.channel.parent_id]
            if data['call_started'] == True: return
        except KeyError:
            return
        ammount = await DMCConverter_Ctx().convert(message, message.content)
        if ammount is not None:
            self.bot.dispatch("bet", message, data)


    @app_commands.command(name="request", description="Request an auction for an item you want to sell")
    @app_commands.describe(item="The item to auction", quantity="The quantity of the item")
    @app_commands.checks.has_any_role(785845265118265376, 785842380565774368)
    @app_commands.autocomplete(item=item_autocomplete)
    async def _request(self, interaction: discord.Interaction, item: str, quantity: int=1):
        config = await self.bot.auction.config.find(interaction.guild.id)
        if not config: 
            return await interaction.response.send_message("Auction is not setup", ephemeral=True)
        if interaction.channel.id != config['request_channel']: 
            return await interaction.response.send_message("This is not the auction request channel please use the auction request channel", ephemeral=True)
        
        item_data = self.bot.dank_items_cache[item]
        embed = discord.Embed(title="Auction Request", description="",color=self.bot.default_color)
        embed.description += "**Item: **" + item + "\n"
        embed.description += f"**Quantity: ** {quantity}\n"
        embed.description += f"**Market Price: ** ⏣ {item_data['price']:,}\n"
        embed.description += f"**Starting Price: ** ⏣ {int((item_data['price']*quantity) / 2):,}\n"
        embed.description += "**Requested By: **" + interaction.user.mention + "\n"

        await interaction.response.send_message(embed=embed, ephemeral=False)
        message = await interaction.original_response()
        thread = await message.create_thread(name=f"Auction Request for {item}", auto_archive_duration=1440)
        await thread.send(f"{interaction.user.mention} To Complete this request, please donate item to serverpool in this thread, you can copy the generated command below and use it in this thread, request will be automatically expired in 5 minutes")
        await thread.add_user(interaction.guild.get_member(270904126974590976))
        await thread.send(f"/serverevents donate quantity: {quantity} item: {item}")
        def check(m: discord.Message):
            if m.author.id != 270904126974590976: return False
            if m.embeds[0].description == "Successfully donated!": return True
        try:
            msg = await interaction.client.wait_for("message", check=check, timeout=500)
            msg = await msg.channel.fetch_message(msg.reference.message_id)
            embed = msg.embeds[0].to_dict()
            items = re.findall(r"\*\*(.*?)\*\*", embed['description'])[0]
            emojis = list(set(re.findall(":\w*:\d*", items)))
            for emoji in emojis :items = items.replace(emoji,"",100); items = items.replace("<>","",100);items = items.replace("<a>","",100);items = items.replace("  "," ",100)
            mathc = re.search(r"(\d+)x (.+)", items)
            item_found = mathc.group(2)
            quantity_found = int(mathc.group(1))
            if item.lower() == item_found.lower() and quantity == quantity_found:
                await thread.send(f"{interaction.user.mention} Request Confirmed, creating auction now nad locking this thread")
                await thread.edit(locked=True,archived=True)
                data = {
                    "_id": thread.id,
                    "channel": thread.parent_id,
                    "item": item,
                    "quantity": quantity,
                    "requested_by": interaction.user.id,
                }
                self.bot.dispatch("auction_request", data, item_data, interaction)
                return
        except asyncio.TimeoutError:
            await thread.send(f"{interaction.user.mention} Request Cancelled, you took too long to confirm, deleting this thread in 20 seconds, you many create new request if you want")
            await asyncio.sleep(20)
            await thread.delete()
            await interaction.delete_original_response()
            return
    
    @commands.Cog.listener()
    async def on_auction_request(self, data, item_data, interaction: discord.Interaction):

        embed = discord.Embed(title="Auction Request", description="",color=self.bot.default_color)
        embed.description += "**Item: **" + data['item'] + "\n"
        embed.description += f"**Quantity: ** {data['quantity']}\n"
        embed.description += f"**Market Price: ** ⏣ {item_data['price']:,}\n"
        embed.description += f"**Requested By: ** <@{data['requested_by']}>\n"

        guild_config = await self.bot.auction.get_config(interaction.guild_id)
        channel = interaction.guild.get_channel(guild_config['queue_channel'])
        message = await channel.send(embed=embed)
        data['_id'] = message.id
        await self.bot.auction.request.insert(data)
        

async def setup(bot):
    await bot.add_cog(Auction(bot))
    