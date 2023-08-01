import enum
import discord
import asyncio
import datetime
import re
from discord.ext import commands
from discord import app_commands
from utils.transformer import DMCConverter
from utils.converters import DMCConverter_Ctx
from utils.views.buttons import Confirm
from discord.ext import tasks
from utils.db import Document
from typing import List
from copy import deepcopy


class Auction_db:
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.mongo['Auction']
        self.config = Document(self.db, 'config')
        self.auction = Document(self.db, 'auctions')
        self.payment = Document(self.db, 'payments')
        self.auction_cache = {}
        self.config_cache = {}
        self.payment_cache = {}

    async def get_config(self, guild_id: int):
        config = self.config_cache.get(guild_id)        
        if not config:
            config = await self.config.find({"_id": guild_id})
            if not config:
                config = {"_id": guild_id,"category": None,"request_channel": None,"queue_channel": None,"bid_channel": None,"payment_channel": None,"payout_channel": None,"log_channel": None,"manager_roles": [], "ping_role": None, "minimum_worth": None}
                await self.config.insert(config)
            self.config_cache[guild_id] = config
        return config

    async def update_config(self, guild_id: int, data: dict):
        await self.config.update(data)
        self.config_cache[guild_id] = data
        return data
    
    async def verfiy_payment(self, user: discord.Member, thread: discord.Thread, item: str, quantity: int):
        def check(m: discord.Message):
            if m.author.id != 270904126974590976: return False
            if m.channel.id != thread.id: return False
            if len(m.embeds) == 0: return False
            if m.embeds[0].description == "Successfully donated!": return True
        
        try:
            message: discord.Message = await self.bot.wait_for('message', check=check, timeout=300)
            message = await thread.fetch_message(message.reference.message_id)
            embed = message.embeds[0]
            items = re.findall(r"\*\*(.*?)\*\*", embed.description)[0]
            emojis = list(set(re.findall(":\w*:\d*", items)))
            for emoji in emojis :items = items.replace(emoji,"",100); items = items.replace("<>","",100);items = items.replace("<a>","",100);items = items.replace("  "," ",100)
            mathc = re.search(r"(\d+)x (.+)", items)
            item_found = mathc.group(2)
            quantity_found = int(mathc.group(1))
            if item.lower() == item_found.lower() and quantity == quantity_found:
                return True
            else:
                return False
        except asyncio.TimeoutError:
            return False

    async def setup(self):
        for guild in await self.config.get_all():
            self.config_cache[guild['_id']] = guild
        for auction in await self.payment.get_all():
            if auction['paid'] == True: continue
            self.payment_cache[auction['thread']] = auction

class Auction(commands.GroupCog):
    def __init__(self, bot):
        self.bot = bot
        self.backend = Auction_db(bot)
        self.bot.auction = self.backend
        self.auction_loop_progress = False
        self.auction_loop.start()
            
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
    
    async def update_message(self, message: discord.Message, data: dict, first:bool):
        if first:
            timestamp30s = int((datetime.datetime.now() + datetime.timedelta(seconds=30)).timestamp())
            embed = message.embeds[0]
            fields = [field.name for field in embed.fields]
            if "Time Left" in fields:
                embed.set_field_at(fields.index("Time Left"), name="Time Left", value=f"<t:{timestamp30s}:R>")
            await message.edit(embed=embed)
        else:
            timestamp10s = int((datetime.datetime.now() + datetime.timedelta(seconds=10)).timestamp())
            embed: discord.Embed = message.embeds[0]
            fields = [field.name for field in embed.fields]
            if "Time Left" in fields:
                embed.set_field_at(fields.index("Time Left"), name="Time Left", value=f"<t:{timestamp10s}:R>")
            if "Current Bidder" in fields:
                embed.set_field_at(fields.index("Current Bidder"), name="Current Bidder", value=f"<@{data['current_bidder']}>")
            if "Current Bid" in fields:
                embed.set_field_at(fields.index("Current Bid"), name="Current Bid", value=f"{data['current_bid']:,}")
            await message.edit(embed=embed)        

    def cog_unload(self):
        self.auction_loop.cancel()

    @tasks.loop(seconds=3)
    async def auction_loop(self):
        if self.auction_loop_progress:
            return
        self.auction_loop_progress = True
        auctions = self.backend.auction_cache.copy()
        for key, value in auctions.items():
            auction = self.backend.auction_cache[key]
            if auction['call_started']: continue
            call_time = auction['last_bet'] + datetime.timedelta(seconds=auction['time_left'])
            if call_time < datetime.datetime.now():
                auction['call_started'] = True
                await auction['thread'].send(f"No Bet was place in last {auction['time_left']} seconds, starting closing calls")
                self.backend.auction_cache[key] = auction
                self.bot.dispatch("auction_calls", auction, 0)
        self.auction_loop_progress = False
    
    @auction_loop.before_loop
    async def before_auction_loop(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_ready(self):
       await self.backend.setup()
    
    @app_commands.command(name="request", description="Request an auction")
    @app_commands.autocomplete(item=item_autocomplete)
    async def request(self, interaction: discord.Interaction, item: str, quantity:int = 1):
        config = await self.backend.get_config(interaction.guild_id)
        if not config:
            return await interaction.response.send_message("Auction is not setup yet!")
        if not config['request_channel']:
            return await interaction.response.send_message("Request channel is not setup yet!")

        item = self.bot.dank_items_cache.get(item)
        if not item:
            return await interaction.response.send_message("Invalid item!")
        if item['price'] * quantity < config['minimum_worth']:
            return await interaction.response.send_message(f"Minimum price of auction is ⏣ {config['minimum_worth']:,}!")
        embed = discord.Embed(title="Auction Request", description="", color=interaction.client.default_color)
        embed.description += f"**Item:** {item['_id']}x{quantity}\n"
        embed.description += f"**Requested by:** {interaction.user.mention}\n"
        embed.description += f"**Market Price:** {item['price']}\n"
        embed.description += f"**Total Price:** {item['price'] * quantity}\n"

        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        thread = await msg.create_thread(name=f"Auction Verification - {interaction.user.name}", auto_archive_duration=1440)
        try:await thread.add_user(interaction.user)
        except:pass
        await thread.send(f"{interaction.user.mention}, Please donate the auction items in this thread to verify your request.")
        await thread.send(f"`/serverevents donate quantity:{quantity} item: {item['_id']}`")
        verified = await self.backend.verfiy_payment(interaction.user, thread, item['_id'], quantity)

        if verified == False:
            await thread.send(f"{interaction.user.mention}, Your request has been Failed to verify!")
            await thread.edit(name=f"Auction Request - {interaction.user.name} - Failed", locked=True, archived=True)
            embed.title += " - Failed"
            await msg.edit(embed=embed)
            return
        await thread.send(f"{interaction.user.mention}, Your request has been verified!")
        data = {
            "_id": interaction.user.id,
            "item": item['_id'],
            "quantity": quantity,
            "donated_at": f"https://canary.discord.com/channels/{interaction.guild_id}/{thread.id}",
            "guild_id": interaction.guild_id,
            "message_id": None,
            "channel_id": None,
        }
        await thread.edit(name=f"Auction Request - {interaction.user.name} - Verified", locked=True, archived=True)
        embed.title += " - Verified"
        await msg.edit(embed=embed)

        queue_embed = discord.Embed(description="", color=interaction.client.default_color)
        queue_embed.set_author(name=f"{interaction.user.name}'s Auction", icon_url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar)
        queue_embed.description += f"**Item:** {item['_id']}\n"
        queue_embed.description += f"**Quantity:** {quantity}\n"
        queue_embed.description += f"**Requested by:** {interaction.user.mention}\n"
        queue_embed.description += f"**Market Price:** ⏣ {item['price']}\n"
        queue_embed.description += f"**Total Price:** ⏣ {item['price'] * quantity}\n"
        queue_embed.description += f"**Donated at:** [Click Here]({data['donated_at']})"
        queue_embed.set_footer(text=f"ID: {interaction.user.id}")

        queue_channel = interaction.guild.get_channel(config['queue_channel'])
        if not queue_channel: return
        view = discord.ui.View()
        view.add_item(discord.ui.Button(style=discord.ButtonStyle.link, url=data['donated_at'], emoji="<tgk_link:1105189183523401828>"))
        qmsg = await queue_channel.send(embed=queue_embed, view=view)
        data['message_id'] = qmsg.id
        data['channel_id'] = qmsg.channel.id
        await self.backend.auction.insert(data)
        
    @app_commands.command(name="start", description="Start an auction")
    async def start(self, interaction: discord.Interaction):
        config = await self.backend.get_config(interaction.guild_id)
        if not config:
            await interaction.response.send_message("Auction is not setup yet!")
        user_roles = [role.id for role in interaction.user.roles]
        if not (set(user_roles) & set(config['manager_roles'])):
            return await interaction.response.send_message("You are not allowed to use this command!", ephemeral=True)
        if not config['bid_channel']:
            return await interaction.response.send_message("Bid channel is not setup yet!")
        if interaction.channel.id != config['bid_channel']:
            return await interaction.response.send_message("You can only use this command in bid channel!", ephemeral=True)
        
        auction_data = await self.backend.auction.find({"guild_id": interaction.guild_id})
        if not auction_data:
            return await interaction.response.send_message("There are no auctions pending!", ephemeral=True)
        item = self.bot.dank_items_cache.get(auction_data['item'])

        starting_big = int((item['price'] * auction_data['quantity'])/2)
        bet_incre = int((item['price'] * auction_data['quantity'])/20)

        embed = discord.Embed(title=f"Auction Starting", description="", color=interaction.client.default_color)
        embed.set_author(name="Auction Manager", icon_url="https://cdn.discordapp.com/emojis/1134834084728815677.webp?size=96&quality=lossless")
        embed.add_field(name="Host", value=interaction.guild.get_member(auction_data['_id']).mention)
        embed.add_field(name="Item", value=f"`{auction_data['quantity']}x` **{item['_id']}**")
        embed.add_field(name="Market Price", value=f"⏣ {item['price']:,}")
        embed.add_field(name="Auctioner", value=interaction.user.mention)
        embed.add_field(name="Starting Bid", value=f"⏣ {starting_big:,}")
        embed.add_field(name="Bet Increment", value=f"⏣ {bet_incre:,}")
        embed.add_field(name="Current Bidder", value="`None`")
        embed.add_field(name="Current Bid", value=f"⏣ {starting_big:,}")
        embed.add_field(name="Time Left", value="`Waiting for start`")

        view = Confirm(interaction.user, 60)
        view.children[0].label = "Start Auction"
        view.children[1].label = "Cancel Auction"
        await interaction.response.send_message(embed=embed, view=view)
        msg = await interaction.original_response()
        view.message = msg
        await view.wait()
        if not view.value:
            return await interaction.delete_original_response()
        else:
            await view.interaction.response.edit_message(view=None)
        thread = await msg.create_thread(name=f"Auction for {item['_id']}", auto_archive_duration=1440)
        data = {
            "_id": thread.id,
            "item": item['_id'],
            "quantity": auction_data['quantity'],
            "price": item['price'],
            "starting_bid": starting_big,
            "current_bid": starting_big,
            "current_bidder": None,
            "bet_increment": bet_incre,
            "auctioner": interaction.user.id,
            "donated_at": auction_data['donated_at'],
            "host": auction_data['_id'],
            "start_at": datetime.datetime.now(),
            "last_bet": datetime.datetime.now(),
            "time_left": 30,
            "call_started": False,
            "thread": thread,
            "message": msg,
            "ended": False
        }
        self.backend.auction_cache[thread.id] = data
        await self.update_message(message=msg, data=data, first=True)
        if config['ping_role']:
            role = interaction.guild.get_role(config['ping_role'])
            if role:
                await interaction.followup.send(f"{role.mention} New auction has been started!", ephemeral=False)
        if config['log_channel']:
            channel = interaction.guild.get_channel(config['log_channel'])
            self.bot.dispatch("auction_start_log", data['auctioner'], data['host'], data['item'], data['quantity'], channel)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot: 
            if message.author.id != 270904126974590976: return
            if message.channel.id in self.backend.payment_cache.keys():
                if len(message.embeds) == 0: return
                if message.embeds[0].description != "Successfully donated!": return
                self.bot.dispatch("payment", message)
            return
        if not message.guild: return
        if not isinstance(message.channel, discord.Thread): return
        try:
            data = self.backend.auction_cache[message.channel.id]
            if data['call_started'] == True: return
        except KeyError:
            return
        ammount = await DMCConverter_Ctx().convert(message, message.content)
        if ammount is not None:
            self.bot.dispatch("bet", message, data)
    
    @commands.Cog.listener()
    async def on_bet(self, message: discord.Message, data: dict):
        ammout = await DMCConverter_Ctx().convert(message, message.content)
        if not isinstance(ammout, int):
            return
        if message.author.id == data['host']:
            return await message.reply("You can't bet on your own auction!")
        if not data['current_bidder']:
            pass
        else:
            if message.author.id == data['current_bidder']:
                return await message.reply("You are already the highest bidder!")
        if ammout >= 50000000000:
            return await message.reply("You can't bet more than ⏣ 50,000,000,000!")
        if ammout > data['current_bid']:
            if ammout - data['current_bid'] < data['bet_increment']:
                return await message.reply(f"Your bet must have at least ⏣ {data['bet_increment']:,} increment from the current bid!")
            data['current_bid'] = ammout
            data['current_bidder'] = message.author.id
            data['last_bet'] = datetime.datetime.now()
            data['time_left'] = 10
            await message.reply(f"You are now the highest bidder with ⏣ {ammout:,}!")
            await message.add_reaction("<:tgk_active:1082676793342951475>")
            await self.update_message(data['message'], data, first=False)
        else:
            return await message.reply(f"Current bid is ⏣ {data['current_bid']:,}! You can't bet less than that!")
    
    @commands.Cog.listener()
    async def on_auction_calls(self, data: dict, call_num:int):
        message: discord.Message = data['message']
        thread: discord.Thread = data['thread']
        if call_num == 0:
            embed = discord.Embed(description=f"# Going Once...", color=self.bot.default_color)
        if call_num == 1:
            embed = discord.Embed(description=f"# Going Twice...", color=self.bot.default_color)
        if call_num >= 2:
            self.bot.dispatch("auction_ended", data)
            return
        call_started = datetime.datetime.now()
        time_passed = 0

        def check(m: discord.Message):
            if m.author.bot: return False
            if m.channel != thread: return False
            if m.author.id == data['host']: return False
            if m.author.id == data['current_bidder']: return False  
            if re.match('^[0-9]+', m.content):
                    return True
        
        await thread.send(embed=embed)
        while True:
            try:
                timeout = 10 - time_passed
                if timeout <= 0: raise asyncio.TimeoutError
                msg = await self.bot.wait_for('message', check=check, timeout=timeout)
                ammout = await DMCConverter_Ctx().convert(msg, msg.content)
                if not isinstance(ammout, int):
                    time_passed = int((datetime.datetime.now() - call_started).total_seconds())
                    continue
                if not ammout:
                    time_passed = int((datetime.datetime.now() - call_started).total_seconds())
                    continue
                if ammout >= 50000000000:
                    await msg.reply("You can't bet more than ⏣ 50,000,000,000!")
                    time_passed = int((datetime.datetime.now() - call_started).total_seconds())
                    continue
                if ammout > data['current_bid']:
                    if ammout - data['current_bid'] < data['bet_increment']:
                        await msg.reply(f"You can't bet less than ⏣ {data['bet_increment']:,} more than the current bid!")
                        time_passed = int((datetime.datetime.now() - call_started).total_seconds())
                        continue
                    else:
                        data['current_bid'] = ammout
                        data['current_bidder'] = msg.author.id
                        data['last_bet'] = datetime.datetime.now()
                        data['time_left'] = 10
                        data['call_started'] = False
                        await msg.reply(f"You are now the highest bidder with ⏣ {ammout:,}!")
                        await msg.add_reaction("<:tgk_active:1082676793342951475>")
                        await self.update_message(data['message'], data, first=False)
                        return
            except asyncio.TimeoutError:
                self.bot.dispatch("auction_calls", data, call_num+1)
                return
    
    @commands.Cog.listener()
    async def on_auction_ended(self, data: dict):
        config = await self.backend.get_config(data['message'].guild.id)
        message: discord.Message = data['message']
        thread: discord.Thread = data['thread']
        third_call = discord.Embed(description="# Going Thrice...", color=self.bot.default_color)
        embed = discord.Embed(description=f"# Sold to <@{data['current_bidder']}> for ⏣ {data['current_bid']:,}!", color=0x00ff00)
        await thread.send(embeds=[third_call, embed])
        await thread.edit(locked=True, archived=True)
        main_embed = message.embeds[0]
        for i in range(3):main_embed.remove_field(-1)    
        main_embed.add_field(name="Sold to", value=f"<@{data['current_bidder']}>")
        main_embed.add_field(name="Winning Bid", value=f"⏣ {data['current_bid']:,}")
        main_embed.add_field(name=" ", value=" ")
        await message.edit(embed=main_embed)
        if data['current_bidder'] == None and data['current_bid'] == data['starting_bid']:
            await message.reply("No one bid on your auction, so it has been cancelled.")
            return
        payout_data = {
            'host': data['host'],
            'bidder': data['current_bidder'],
            'bid': data['current_bid'],
            'item': data['item'],
            'quantity': data['quantity'],
            "paid": False,
        }
        payout_channel = self.bot.get_channel(config['payment_channel'])

        embed = discord.Embed(color=self.bot.default_color, description="")
        embed.set_author(name="Auction Manager", icon_url="https://cdn.discordapp.com/emojis/1134834084728815677.webp?size=96&quality=lossless")
        embed.description += f"**Auction Winner:** <@{payout_data['bidder']}>\n"
        embed.description += f"**Auction Host:** <@{payout_data['host']}>\n"
        embed.description += f"**Item:** {payout_data['quantity']}{payout_data['item']}\n"
        embed.description += f"**Price:** ⏣ {payout_data['bid']:,}\n"

        msg:discord.Message = await payout_channel.send(embed=embed, content=f"<@{payout_data['bidder']}>, Please pay {payout_data['bid']:,} in the thread below to confirm your purchase!")
        payout_data['_id'] = msg.id
        thread = await msg.create_thread(name=f"Auction Payment", auto_archive_duration=1440)
        await thread.send(f"/serverevents donate quantity: {payout_data['bid']}")
        payout_data['thread'] = thread.id
        self.backend.payment_cache[thread.id] = payout_data
        await self.backend.payment.insert(payout_data)
        try:
            self.backend.auction_cache.pop(thread.id)
        except:
            pass
        queue_data = await self.backend.auction.find({'_id': data['host']})
        await self.backend.auction.delete({'_id': data['host']})
        if queue_data:
            channel = message.guild.get_channel(config['queue_channel'])
            try:
                msg = await channel.fetch_message(queue_data['message_id'])
                embed = msg.embeds[0]
                embed.author.name += " (Ended)"
                await msg.edit(embed=embed)
            except:
                pass
        config = await self.backend.get_config(message.guild.id)
        if config['log_channel']:
            log_channel = message.guild.get_channel(config['log_channel'])
            self.bot.dispatch("auction_ended", data['auctioner'], data['host'], data['message'], log_channel, data['item'], data['quantity'], payout_data['bid'])

    
    @commands.Cog.listener()
    async def on_payment(self, message: discord.Message):
        data = await self.backend.payment.find({'thread': message.channel.id})
        if not message.reference:
            return
        try:
            donate_mesage = await message.channel.fetch_message(message.reference.message_id)
        except:
            return
        embed: discord.Embed = donate_mesage.embeds[0]
        items = re.findall(r"\*\*(.*?)\*\*", embed.description)[0]
        quantity = int(items.replace("⏣", "", 100).replace(",", "", 100))        
        if not isinstance(quantity, int): 
            return
        if quantity !=  data['bid']:
            return await message.channel.send(f"<@{data['bidder']}>, You have to pay ⏣ {data['bid']:,}!")
        await message.channel.send(f"<@{data['bidder']}>, Thank you for your payment! your items will be delivered shortly!")
        data['paid'] = True
        await self.backend.payment.update(data)
        await message.channel.send(f"<@{data['host']}>, We have received the payment for your auction! your payment will be credited shortly!")
        try:
            self.backend.payment_cache.pop(data['thread'])
        except:
            pass
        await message.channel.send("Dank Manager, Here is your commands for this auction:")
        await message.channel.send(f"/serverevents payout user:{data['host']} quantity:{data['bid']}")
        await message.channel.send(f"/serverevents payout user:{data['bidder']} quantity:{data['quantity']} item:{data['item']}")

    @commands.Cog.listener()
    async def on_auction_start_log(self, user: int, host: int, message: discord.Message, log_channel: discord.TextChannel, item: str, quantity: str, ):
        embed = discord.Embed(color=self.bot.default_color, description="", title="Auction | Started")
        embed.set_author(name="Auction Manager", icon_url="https://cdn.discordapp.com/emojis/1134834084728815677.webp?size=96&quality=lossless")
        embed.add_field(name="Auctioneer", value=f"<@{user}>")
        embed.add_field(name="Host", value=f"<@{host}>")
        embed.add_field(name="Item", value=f"{quantity}x{item}")
        embed.add_field(name="Message", value=f"[Click Here]({message.jump_url})")
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Jump", style=discord.ButtonStyle.link, url=message.jump_url, emoji="<:tgk_link:1105189183523401828>"))
        await log_channel.send(embed=embed, view=view)

    @commands.Cog.listener()
    async def on_auction_end_log(self, user: int, host: int, winner: int, message: discord.Message, log_channel: discord.TextChannel, item: str, quantity: str, bid: int):
        embed = discord.Embed(color=self.bot.default_color, description="", title="Auction | Ended")
        embed.set_author(name="Auction Manager", icon_url="https://cdn.discordapp.com/emojis/1134834084728815677.webp?size=96&quality=lossless")
        embed.add_field(name="Auctioneer", value=f"<@{user}>")
        embed.add_field(name="Host", value=f"<@{host}>")
        embed.add_field(name="Winner", value=f"<@{winner}>")
        embed.add_field(name="Item", value=f"{quantity}x{item}")
        embed.add_field(name="Bid", value=f"⏣ {bid:,}")
        embed.add_field(name="Message", value=f"[Click Here]({message.jump_url})")
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Jump", style=discord.ButtonStyle.link, url=message.jump_url, emoji="<:tgk_link:1105189183523401828>"))
        await log_channel.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Auction(bot))
