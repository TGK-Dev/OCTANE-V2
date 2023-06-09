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
            embed.description += f"**Highest Bid:** ⏣ {data['current_bid']:,}\n"
            embed.description += f"**Current Bid By:** {winner.mention}\n"
            embed.description += f"**Time Left:** `Auction Ended`\n"
            embed.description += f"**Auctioneer:** <@{data['auctioneer']}>\n"
            return embed
        
        if first:
            timestamp30s = int((datetime.datetime.now() + datetime.timedelta(seconds=30)).timestamp())
            embed = discord.Embed(title=f"Auction for {data['item']}", description="", color=self.bot.default_color)
            embed.description += f"**Starting Bid:** ⏣ {data['strating_price']:,}\n"
            embed.description += f"**Bet Multiplier:** ⏣ {data['bet_multiplier']:,}\n"  
            embed.description += f"**Highest Bid:** `None`\n"
            embed.description += f"**Current Bid By:** `None`\n"
            embed.description += f"**Time Left:** <t:{timestamp30s}:R>\n"
            embed.description += f"**Auctioneer:** <@{data['auctioneer']}>\n"
            return embed
        else:
            timestamp10s = int((datetime.datetime.now() + datetime.timedelta(seconds=10)).timestamp())
            embed = discord.Embed(title=f"Auction for {data['item']}", description="", color=self.bot.default_color)
            embed.description += f"**Starting Bid:** ⏣ {data['strating_price']:,}\n"
            embed.description += f"**Bet Multiplier:** ⏣ {data['bet_multiplier']:,}\n"
            embed.description += f"**Highest Bid:** ⏣ {data['current_bid']:,}\n"
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
                self.bot.dispatch("auction_end_count", auction)
                try:
                    del self.bid_cache[auction['_id']]
                except KeyError:
                    pass
        self.auction_loop_progress = False

    @auction_loop.before_loop
    async def before_auction_loop(self):
        await self.bot.wait_until_ready()
    
    @commands.Cog.listener()
    async def on_bet(self, message: discord.Message, data):
        ammount = await DMCConverter_Ctx().convert(message, message.content)
        if ammount % data["bet_multiplier"] != 0:
            await message.reply(f"Mininum Bid Increment is ⏣ {data['bet_multiplier']:,}")
            return
        if ammount >= 50000000000:
            await message.reply("You can't bid more than ⏣ 50,000,000,000")
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
    
    @commands.Cog.listener()
    async def on_auction_end_count(self, data):
        message: discord.Message = data['message']
        thread: discord.Thread = data['thread']
        await thread.send(f"No Bet was place in last 10 seconds, starting closing calls")
        await asyncio.sleep(1)
        cembed = discord.Embed(description=f"# Going Once...", color=self.bot.default_color)
        await thread.send(embed=cembed)
        final_call = 0
        ammout = None
        def check(m):
            if m.channel == thread:
                if re.match('^[0-9]+', m.content):
                    return True
        while ammout == None:
            async with thread.typing():
                try:
                    msg = await self.bot.wait_for("message", check=check, timeout=10)
                    ammout = await DMCConverter_Ctx().convert(msg, msg.content)
                    if ammout is not None:
                        if ammout >= 50000000000:
                            await message.reply("You can't bid more than ⏣ 50,000,000,000")
                            continue
                        if ammout > data['current_bid'] and ammout % data['bet_multiplier'] == 0:
                            data['current_bid'] = ammout
                            if data['current_bid_by'] == msg.author.id: 
                                await msg.reply("You are already the highest bidder")
                            
                            data['current_bid_by'] = msg.author.id
                            data['time_left'] = 10
                            data['last_bid'] = datetime.datetime.now()

                            embed = await self.get_embed(data, False)
                            await message.edit(embed=embed)
                            await msg.add_reaction("✅")
                            await msg.reply(f"You have bid ⏣ {ammout:,} on {data['item']}")

                            self.bid_cache[data['_id']] = data
                            return
                    else:
                        raise ValueError
                except (asyncio.TimeoutError, ValueError):
                    final_call += 1
                    if final_call == 1:
                        ammout = None
                        embed = discord.Embed(description=f"# Going twice...", color=self.bot.default_color)
                        await thread.send(embed=embed)
                        continue
                    elif final_call == 2:
                        ammout = None
                        embed1 = discord.Embed(description=f"# Going thrice...", color=self.bot.default_color)
                        embed = discord.Embed(description=f"# Sold", color=self.bot.default_color)
                        await thread.send(embeds=[embed1,embed])
                        await thread.parent.send(f"Congratulations <@{data['current_bid_by']}>, you have won the auction for {data['item']} for ⏣ {data['current_bid']:,}")
                        await message.edit(embed=await self.get_embed(data, False, message.guild.get_member(data['current_bid_by'])))
                        await thread.edit(archived=True, locked=True)
                        return

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.guild is None:
            return
        if not isinstance(message.channel, discord.Thread): return
        try:
            data = self.bid_cache[message.channel.parent_id]
        except KeyError:
            return
        ammount = await DMCConverter_Ctx().convert(message, message.content)
        if ammount is not None:
            self.bot.dispatch("bet", message, data)


    @app_commands.command(name="start", description="Starts an auction")
    @app_commands.describe(item="The item to auction", bet_multiplier="The bet multiplier")
    @app_commands.autocomplete(item=item_autocomplete)
    async def start(self, interaction: discord.Interaction, item: str, bet_multiplier: app_commands.Transform[int, DMCConverter] = 100000):
        if interaction.channel.id in self.bid_cache.keys():
            await interaction.response.send_message("There is already an auction in this channel", ephemeral=True)
            return
        timestamp30s = int(round((datetime.datetime.now() + datetime.timedelta(seconds=30)).timestamp()))
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
            'thread': None
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
    