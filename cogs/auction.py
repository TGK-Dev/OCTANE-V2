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


class Auction(commands.GroupCog, name="auction"):
    def __init__(self, bot):
        self.bot = bot
        self.bid_cache = {}
        self.bot.autcions = Document(self.bot.db, "auction")
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
            embed = discord.Embed(title=f"Auction for {data['item']}", description="", color=self.bot.default_color)
            embed.description += f"**Starting Bid:** ⏣ {data['strating_price']:,}\n"
            embed.description += f"**Bet Multiplier:** ⏣ {data['bet_multiplier']:,}\n"  
            embed.description += f"**Bid Increment By:** ⏣ {data['current_bid']:,}\n"
            embed.description += f"**Current Bid By:** {winner.mention}\n"
            embed.description += f"**Time Left:** `Auction Ended`\n"
            embed.description += f"**Auctioneer:** <@{data['auctioneer']}>\n"
            return embed
        
        if first:
            timestamp30s = int((datetime.datetime.now() + datetime.timedelta(seconds=30)).timestamp())
            embed = discord.Embed(title=f"Auction for {data['item']}", description="", color=self.bot.default_color)
            embed.description += f"**Starting Bid:** ⏣ {data['strating_price']:,}\n"
            embed.description += f"**Bet Multiplier:** ⏣ {data['bet_multiplier']:,}\n"  
            embed.description += f"**Bid Increment By:** `None`\n"
            embed.description += f"**Current Bid By:** `None`\n"
            embed.description += f"**Time Left:** <t:{timestamp30s}:R>\n"
            embed.description += f"**Auctioneer:** <@{data['auctioneer']}>\n"
            return embed
        else:
            timestamp10s = int((datetime.datetime.now() + datetime.timedelta(seconds=10)).timestamp())
            embed = discord.Embed(title=f"Auction for {data['item']}", description="", color=self.bot.default_color)
            embed.description += f"**Starting Bid:** ⏣ {data['strating_price']:,}\n"
            embed.description += f"**Bet Multiplier:** ⏣ {data['bet_multiplier']:,}\n"
            embed.description += f"**Bid Increment By:** ⏣ {data['current_bid']:,}\n"
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
                if m.author.id == data['current_bid_by']: return False
                if re.match('^[0-9]+', m.content):
                    return True              
        await thread.send(embed=embed)

        while True:
            try:
                timeout = 10 - time_passed
                if timeout <= 0: raise asyncio.TimeoutError
                print("waiting for Bet")
                print(timeout)
                print("------------------")
                print("call_num", call_num)
                print("------------------")
                msg = await self.bot.wait_for('message', check=check, timeout=timeout)
                ammout = await DMCConverter_Ctx().convert(msg, msg.content)
                print(ammout, "Ammout")
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
                    await thread.send(f"New Bid of ⏣ {ammout:,} by <@{msg.author.id}>")
                    embed = await self.get_embed(data)
                    await data['message'].edit(embed=embed)
                    print(timeout, "Success")
                    return
            except asyncio.TimeoutError:
                data['call_count'] += 1
                self.bot.dispatch('auction_calls', data, data['call_count'], 10)
                print(int((datetime.datetime.utcnow() - call_started_at).total_seconds()))
                return
        
                
    
    @commands.Cog.listener()
    async def on_bet(self, message: discord.Message, data):
        ammount = await DMCConverter_Ctx().convert(message, message.content)
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


    @app_commands.command(name="start", description="Starts an auction")
    @app_commands.describe(item="The item to auction", bet_multiplier="The bet multiplier")
    @app_commands.autocomplete(item=item_autocomplete)
    @app_commands.rename(bet_multiplier="bet-increments")
    @app_commands.choices(bet_multiplier=[
        app_commands.Choice(name="1k", value=1000),
        app_commands.Choice(name="10k", value=10000),
        app_commands.Choice(name="100k", value=100000),
        app_commands.Choice(name="1m", value=1000000),
    ])
    async def start(self, interaction: discord.Interaction, item: str, bet_multiplier: int):
        if interaction.channel.id in self.bid_cache.keys():
            await interaction.response.send_message("There is already an auction in this channel", ephemeral=True)
            return
        item_data = self.bot.dank_items_cache[item]
        strating_price = int(item_data["price"] / 2)
        data = {
            '_id': interaction.channel.id,
            'item': item,
            'strating_price': strating_price,
            'bet_multiplier': bet_multiplier,
            'current_bid': strating_price,            
            'current_bid_by': None,
            'time_left': 30,
            'last_bid': None,
            'message': None,
            'auctioneer': interaction.user.id,
            'thread': None,
            'call_started': False,
            'call_count': 0,
        }

        embed = await self.get_embed(data, True)

        await interaction.response.send_message(embed=embed, ephemeral=False)
        msg = await interaction.original_response()
        thread = await msg.create_thread(name=f"Auction for {item}", auto_archive_duration=1440)
        data['message'] = msg
        data['thread'] = thread

        self.bid_cache[interaction.channel.id] = data

async def setup(bot):
    await bot.add_cog(Auction(bot))
    