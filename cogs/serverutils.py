import random
import re
import discord
import datetime
import asyncio
import humanfriendly
from discord import app_commands
from discord.ext import commands, tasks
import pandas as pd
from utils.converters import millify
from utils.db import Document
from utils.transformer import MultipleMember, DMCConverter
from utils.views.payout_system import Payout_Buttton, Payout_claim
from utils.views.buttons import Confirm
from typing import List
from io import BytesIO
from typing import Union
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageChops

auto_payout = {
    1040975933772931172: {'prize': 1, 'event': 'Daily Rumble', 'item': 'Pepe Trophy'}, #pepet
    1042408506181025842: {'prize': 100000000, 'event': 'Weekly Rumble', 'item': None}, #100m 
    1110476759062827008: {'prize': 6900000, 'event': '100-Players Rumble', 'item': None},
    1111603846943354930: {'prize': 1, 'event': 'Bday Ru', 'item': 'Pepe Trophy'}, #pepet
    
}		

class Payout(commands.GroupCog, name="payout", description="Payout commands"):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.mongo['Payout_System']
        self.bot.payout_config = Document(self.db, "payout_config")
        self.bot.payout_queue = Document(self.db, "payout_queue")
        self.bot.payout_pending = Document(self.db, "payout_pending")
        self.bot.payout_delete_queue = Document(self.db, "payout_delete_queue")
        self.claim_task = self.check_unclaim.start()
        self.bot.create_payout = self.create_payout
        self.claim_task_progress = False
        self.comman_event = ["Mega Giveaway", "Daily Giveaway", "Silent Giveaway", "Black Tea", "Rumble Royale", "Hunger Games", "Guess The Number", "Split Or Steal", "Mafia", "Typerace", "Bingo", "Heist Giveaway"]
    
    async def event_auto_complete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        _list = [
            app_commands.Choice(name=event, value=event)
            for event in self.comman_event if event.lower() in current.lower()
        ]
        if len(_list) == 0:
            return [
                app_commands.Choice(name=event, value=event)
                for event in self.comman_event
            ]
        return _list[:24]

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
    
    async def create_pending_embed(self, event: str, winner: discord.Member, prize: str, channel: discord.TextChannel, message: discord.Message, claim_time: int, host: discord.Member, item_data: dict) -> discord.Embed:
        embed = discord.Embed(title="Payout Queue", timestamp=datetime.datetime.now(), description="", color=self.bot.default_color)
        embed.description += f"**Event:** {event}\n"
        embed.description += f"**Winner:** {winner.mention}\n"
        if item_data != None:
            embed.description += f"**Prize:** `{prize}x {item_data['_id']}`\n"
        else:
            embed.description += f"**Prize:** `⏣ {prize:,}`\n"
        embed.description += f"**Channel:** {channel.mention}\n"
        embed.description += f"**Message:** [Click Here]({message.jump_url})\n"
        embed.description += f"**Claim Time:** <t:{int(claim_time)}:R>\n"
        embed.description += f"**Set By:** {host.mention}\n"
        embed.description += f"**Status:** `Pending`"
        embed.set_footer(text=f"ID: {message.id}")
        if item_data != None:
            value = f"**Name**: {item_data['_id']}\n"
            value += f"**Price**: ⏣ {item_data['price']:,}\n"
            value += f"Total Value of this payout with {prize}x {item_data['_id']} is ⏣ {prize * item_data['price']:,}"
            embed.add_field(name="Item Info", value=value)
        return embed

    async def create_payout(self, event: str, winner: discord.Member, host: discord.Member, prize: int, message: discord.Message, item: dict=None):
        config = await self.bot.payout_config.find(message.guild.id)
        queue_data = {
            '_id': None,
            'channel': message.channel.id,
            'guild': message.guild.id,
            'winner': winner.id,
            'prize': prize,
            'item': item['_id'] if item else None,
            'event': event,
            'claimed': False,
            'set_by': host.id,
            'winner_message_id': message.id,
            'queued_at': datetime.datetime.now(), 
            'claim_time': config['default_claim_time']
            }
        claim_time_timestamp = int((datetime.datetime.now() + datetime.timedelta(seconds=int(config['default_claim_time']))).timestamp())
        embed = await self.create_pending_embed(event, winner, prize, message.channel, message, claim_time_timestamp, host, item)
        claim_channel = message.guild.get_channel(config['pending_channel'])
        if not claim_channel: return		
        claim_message = await claim_channel.send(embed=embed, view=Payout_claim(), content=f"{winner.mention} Your prize has been queued for payout. Please claim it within <t:{claim_time_timestamp}:R> or it will rerolled.")
        queue_data['_id'] = claim_message.id
        await self.bot.payout_queue.insert(queue_data)
        await message.add_reaction("<a:loading:998834454292344842>")

    def cog_unload(self):
        self.claim_task.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(Payout_Buttton())
        self.bot.add_view(Payout_claim())

    @tasks.loop(seconds=10)
    async def check_unclaim(self):
        if self.claim_task_progress: return
        self.claim_task_progress = True
        data = await self.bot.payout_queue.get_all()
        for payout in data:
            now = datetime.datetime.utcnow()
            if now > payout['queued_at'] + datetime.timedelta(seconds=payout['claim_time']):
                await asyncio.sleep(2)
                view = discord.ui.View()
                view.add_item(discord.ui.Button(label="Claim period expired!", style=discord.ButtonStyle.gray, disabled=True, emoji="<a:nat_cross:1010969491347357717>"))
                payout_config = await self.bot.payout_config.find(payout['guild'])
                guild = self.bot.get_guild(payout['guild'])
                channel = guild.get_channel(payout_config['pending_channel'])
                if not channel:
                    await self.bot.payout_queue.delete(payout['_id'])
                    continue
                try:
                    message = await channel.fetch_message(payout['_id'])
                except discord.NotFound:
                    await self.bot.payout_queue.delete(payout['_id'])
                    continue
                embed = message.embeds[0]
                embed.title = "Payout Expired"
                embed.description = embed.description.replace("`Pending`", "`Expired`")
                await message.edit(embed=embed,view=view, content=f"<@{payout['winner']}> you have not claimed your payout in time.")
                host = guild.get_member(payout['set_by'])
                dm_view = discord.ui.View()
                dm_view.add_item(discord.ui.Button(label="Payout Message Link", style=discord.ButtonStyle.url, url=message.jump_url))
                user = guild.get_member(payout['winner'])

                event_channel = guild.get_channel(payout['channel'])
                if not event_channel:
                    await self.bot.payout_queue.delete(payout['_id'])
                    continue
                try:
                    event_message = await event_channel.fetch_message(payout['winner_message_id'])
                    loading_emoji = await self.bot.emoji_server.fetch_emoji(998834454292344842)
                    for reactions in event_message.reactions:
                        if reactions.emoji == loading_emoji:
                            async for user in reactions.users():
                                if user.id == self.bot.user.id:
                                    await event_message.remove_reaction(loading_emoji, user)
                                    break							
                            break
                except discord.NotFound:
                    pass

                self.bot.dispatch("payout_expired", message, user)
                if host:
                    if host.id != self.bot.user.id:
                        try:
                            await host.send(f"<@{payout['winner']}> has failed to claim within the deadline. Please reroll/rehost the event/giveaway.", view=dm_view)
                        except discord.HTTPException:
                            pass

                await self.bot.payout_queue.delete(payout['_id'])
            else:
                continue

            await asyncio.sleep(1)

        self.claim_task_progress = False	

    @check_unclaim.before_loop
    async def before_check_unclaim(self):
        await self.bot.wait_until_ready()
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild is None or message.guild.id != 785839283847954433: return
        if not message.author.bot: return
        if message.author.id != 693167035068317736: return
        if message.channel.id not in auto_payout.keys(): return
        if len(message.embeds) == 0: return

        embed = message.embeds[0]
        if embed.title != "<:Crwn2:872850260756664350> **__WINNER!__**" and len(message.mentions) == 1:
            return
        if len(message.mentions) == 0: return
        winner = message.mentions[0]
        auto_payout_data = auto_payout[message.channel.id]
        if auto_payout_data['item'] is not None:
            item = await self.bot.dank_items.find(auto_payout_data['item'])
            if item:
                await self.create_payout(auto_payout_data['event'], winner, self.bot.user, auto_payout_data['prize'], message, item)
        else:
            await self.create_payout(auto_payout_data['event'], winner, self.bot.user, auto_payout_data['prize'], message)

    @app_commands.command(name="set", description="configur the payout system settings")
    @app_commands.describe(event="event name", message_id="winner message id", winners="winner of the event", quantity='A constant number like "123" or a shorthand like "5m"', item="what item did they win?")
    @app_commands.autocomplete(event=event_auto_complete)
    @app_commands.autocomplete(item=item_autocomplete)
    async def payout_set(self, interaction: discord.Interaction, event: str, message_id: str, winners: app_commands.Transform[discord.Member, MultipleMember], quantity: app_commands.Transform[int, DMCConverter], item: str=None):
        data = await self.bot.payout_config.find(interaction.guild.id)
        if data is None: return await interaction.response.send_message("Payout system is not configured yet!", ephemeral=True)
        user_roles = [role.id for role in interaction.user.roles]
        if (set(user_roles) & set(data['event_manager_roles'])):
            pass
        else:
            return await interaction.response.send_message("You are not allowed to use this command!", ephemeral=True)
        
        claim_time_seconds = data['default_claim_time'] if data['default_claim_time'] is not None else 86400
        try:
            event_message = await interaction.channel.fetch_message(message_id)
        except discord.NotFound:
            return await interaction.response.send_message("Error: Message not found! Please make sure you have the correct message id and in the same channel as this command.", ephemeral=True)
        
        claim_channel = interaction.guild.get_channel(data['pending_channel'])
        if claim_channel is None:
            return await interaction.response.send_message("Error: Claim channel not found! Please make sure your configured claim channel is still valid.", ephemeral=True)
    
        claim_time_timestamp = int(round((datetime.datetime.now() + datetime.timedelta(seconds=claim_time_seconds)).timestamp()))

        confrim_embed = discord.Embed(title="Payout confirmation", description="", color=interaction.client.default_color)
        confrim_embed.description += f"**Event:** {event}\n"
        confrim_embed.description += f"**Winners:** {', '.join([winner.mention for winner in winners])}\n"
        if item:
            item_data = await interaction.client.dank_items.find(item)
            if not item_data:
                return await interaction.response.send_message("Error: Item not found! Please make sure you have the correct item name.", ephemeral=True)
            confrim_embed.description += f"**Prize:** {quantity} x {item}\n"
        else:
            confrim_embed.description += f"**Prize: ⏣ {quantity:,} Each**\n"
            item_data = None
        confrim_embed.description += f"**Message** {event_message.jump_url}\n"
        confrim_embed.description += f"**Claim Time:** {humanfriendly.format_timespan(claim_time_seconds)}\n"
        confrim_embed.add_field(name="Warning", value=f"**By clicking on the button below, you confirm that all information is correct and you will be responsible for any incorrect information provided.**")

        view = Confirm(interaction.user, 60)
        view.children[0].label = "Confirm"
        view.children[0].style = discord.ButtonStyle.green
        view.children[1].label = "Cancel"
        view.children[1].style = discord.ButtonStyle.red
        
        await interaction.response.send_message(embed=confrim_embed, view=view, ephemeral=True)
        view.message = await interaction.original_response()

        await view.wait()

        loading_embed = discord.Embed(description=f"<a:loading:998834454292344842> | Setting up the payout for total of `{len(winners)}` winners!")
        loading_embed.set_footer(text="This might take a while depending on the number of winners.")

        if view.value is None or view.value is False:
            return await interaction.delete_original_response()
        else:
            await view.interaction.response.edit_message(view=None, embed=loading_embed)
        
        for winner in winners:
            queue_data = await self.bot.payout_queue.find({'winner_message_id': event_message.id, 'winner': winner.id})
            pending_data = await self.bot.payout_queue.find({'winner_message_id': event_message.id, 'winner': winner.id})

            if queue_data != None or pending_data != None:
                loading_embed.description += f"\n<:dynoError:1000351802702692442> | Failed to queue payout for {winner.mention} `({winner.global_name})` due to possible duplicate entry."
                await interaction.edit_original_response(embed=loading_embed)
                continue
            embed = await self.create_pending_embed(event, winner, quantity, event_message.channel, event_message, claim_time_timestamp, interaction.user, item_data)
            msg = await claim_channel.send(embed=embed, view=Payout_claim(), content=f"{winner.mention} Your prize has been queued for payout. Please claim it within <t:{claim_time_timestamp}:R> or it will rerolled.")

            queue_data = {
                '_id': msg.id,
                'channel': event_message.channel.id,
                'guild': event_message.guild.id,
                'winner': winner.id,
                'prize': quantity,
                'item': item if item else None,
                'event': event,
                'claimed': False,
                'set_by': interaction.user.id,
                'winner_message_id': event_message.id,
                'queued_at': datetime.datetime.now(), 
                'claim_time': claim_time_seconds}

            if winners.index(winner) == 0:
                link_view = discord.ui.View()
                link_view.add_item(discord.ui.Button(label="Queued Payouts", url=msg.jump_url, style=discord.ButtonStyle.link))
                await interaction.edit_original_response(view=link_view)
            
            try:
                await interaction.client.payout_queue.insert(queue_data)
                loading_embed.description += f"\n<:octane_yes:1019957051721535618> | Payout Successfully queued for {winner.mention} `({winner.global_name})`"
            except Exception as e:
                loading_embed.description += f"\n<:dynoError:1000351802702692442> | Failed to queue payout for {winner.mention} `({winner.global_name})`"

            await interaction.edit_original_response(embed=loading_embed)
            self.bot.dispatch("payout_queue", interaction.user, event, event_message, msg, winner, quantity)
            await asyncio.sleep(0.75)

        await asyncio.sleep(2)

        done_embed = discord.Embed(description=f"**Successfully queued payout for `{len(winners)}` winners!**", color=interaction.client.default_color)
        done_embed.set_footer(text="You can view the queued payouts by clicking on the button below.")
        await event_message.add_reaction("<a:loading:998834454292344842>")
        await interaction.edit_original_response(embed=done_embed)
    
    @app_commands.command(name="search", description="Search for a payout queue entry.")
    @app_commands.describe(
        message="The message ID of the event message.",
    )
    async def search(self, interaction: discord.Interaction, message: str):
        config = await self.bot.payout_config.find(interaction.guild.id)
        if config == None:
            return await interaction.response.send_message("You need to setup the bot first!", ephemeral=True)
        user_roles = [role.id for role in interaction.user.roles]
        if (set(user_roles) & set(config['event_manager_roles'])):
            pass
        else:
            return await interaction.response.send_message("You are not allowed to use this command!", ephemeral=True)
        data = await interaction.client.payout_queue.find_many_by_custom({'winner_message_id': int(message)})
        embed = discord.Embed(title="Claim Payout Search", color=interaction.client.default_color, description="")
        queue_channel = interaction.guild.get_channel(config['pending_channel'])
        if len(data) == 0:
            embed.description += "\n\n**No pending payouts found for that message!**"
        else:
            i = 1
            for entey in data:
                embed.description += f"\n**{i}.** https://discord.com/channels/{interaction.guild.id}/{queue_channel.id}/{entey['_id']}"
                i += 1
        
        data = await interaction.client.payout_pending.find_many_by_custom({'winner_message_id': int(message)})
        pending_embed = discord.Embed(title="Pending Payout Search", color=interaction.client.default_color, description="")
        pendIn_channel = interaction.guild.get_channel(config['queue_channel'])
        if len(data) == 0:
            pending_embed.description += "\n\n**No pending payouts found for that message!**"
        else:
            i = 0
            for entey in data:
                pending_embed.description += f"\n**{i}.** https://discord.com/channels/{interaction.guild.id}/{pendIn_channel.id}/{entey['_id']}"
                i += 1
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await interaction.followup.send(embed=pending_embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_payout_queue(self, host: discord.Member,event: str, win_message: discord.Message, queue_message: discord.Message, winner: discord.Member, prize: str, item: str = None):
        embed = discord.Embed(title="Payout | Queued", color=discord.Color.green(), timestamp=datetime.datetime.now(), description="")
        embed.description += f"**Host:** {host.mention}\n"
        embed.description += f"**Event:** {event}\n"
        embed.description += f"**Winner:** {winner.mention} ({winner.global_name})\n"
        embed.description += f"**Prize:** {prize:,}\n"
        embed.description += f"**Event Message:** [Jump to Message]({win_message.jump_url})\n"
        embed.description += f"**Queue Message:** [Jump to Message]({queue_message.jump_url})\n"
        embed.set_footer(text=f"Queue Message ID: {queue_message.id}")

        config = await self.bot.payout_config.find(queue_message.guild.id)
        if config is None: return
        log_channel = queue_message.guild.get_channel(config['log_channel'])
        if log_channel is None: return
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_payout_claim(self, message: discord.Message, user: discord.Member):
        embed = discord.Embed(title="Payout | Claimed", color=discord.Color.green(), timestamp=datetime.datetime.now(), description="")
        embed.description += f"**User:** {user.mention}\n"
        embed.description += f"**Queue Message:** [Jump to Message]({message.jump_url})\n"
        embed.set_footer(text=f"Queue Message ID: {message.id}")

        config = await self.bot.payout_config.find(message.guild.id)
        if config is None: return
        log_channel = message.guild.get_channel(config['log_channel'])
        if log_channel is None: return
        await log_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_payout_pending(self, message: discord.Message):
        embed = discord.Embed(title="Payout | Pending", color=discord.Color.yellow(), timestamp=datetime.datetime.now(), description="")
        embed.description += f"**Queue Message:** [Jump to Message]({message.jump_url})\n"
        embed.set_footer(text=f"Queue Message ID: {message.id}")

        config = await self.bot.payout_config.find(message.guild.id)
        if config is None: return
        log_channel = message.guild.get_channel(config['log_channel'])
        if log_channel is None: return
        await log_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_payout_paid(self, message: discord.Message, user: discord.Member, winner: discord.Member, prize: str):
        embed = discord.Embed(title="Payout | Paid", color=discord.Color.dark_green(), timestamp=datetime.datetime.now(), description="")
        embed.description += f"**User:** {user.mention}\n"
        embed.description += f"**Winner:** {winner.mention} ({winner.global_name})\n"
        embed.description += f"**Prize:** {prize}\n"
        embed.description += f"**Queue Message:** [Jump to Message]({message.jump_url})\n"
        embed.set_footer(text=f"Queue Message ID: {message.id}")

        config = await self.bot.payout_config.find(message.guild.id)
        if config is None: return
        log_channel = message.guild.get_channel(config['log_channel'])
        if log_channel is None: return
        await log_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_payout_expired(self, message: discord.Message, user: discord.Member):
        embed = discord.Embed(title="Payout | Expired", color=discord.Color.red(), timestamp=datetime.datetime.now(), description="")
        embed.description += f"**User:** {user.mention}\n"
        embed.description += f"**Queue Message:** [Jump to Message]({message.jump_url})\n"
        embed.set_footer(text=f"Queue Message ID: {message.id}")

        config = await self.bot.payout_config.find(message.guild.id)
        if config is None: return
        log_channel = message.guild.get_channel(config['log_channel'])
        if log_channel is None: return
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_payout_confirmed(self, message: discord.Message, user: discord.Member, winner: discord.Member, payout_channel: discord.TextChannel,data: dict, interaction: discord.Interaction):
        def check(m: discord.Message):
            if m.channel.id != payout_channel.id: 
                return False
            if m.author.id != 270904126974590976:
                return False
            
            if len(m.embeds) == 0: 
                return False
            embed = m.embeds[0]
            if embed.description.startswith("Successfully paid"):

                found_winner = message.guild.get_member(int(embed.description.split(" ")[2].replace("<", "").replace(">", "").replace("!", "").replace("@", ""))) 
                if winner.id != found_winner.id: 
                    return False
                items = re.findall(r"\*\*(.*?)\*\*", embed.description)[0]
                if "⏣" in items:
                    items = int(items.replace("⏣", "").replace(",", ""))
                    if items == data['prize']:
                        return True
                    else:
                        return False
                else:
                    emojis = list(set(re.findall(":\w*:\d*", items)))
                    for emoji in emojis :items = items.replace(emoji,"",100); items = items.replace("<>","",100);items = items.replace("<a>","",100);items = items.replace("  "," ",100)
                    mathc = re.search(r"(\d+)x (.+)", items)
                    item_found = mathc.group(2)
                    quantity_found = int(items.split(" ")[0][:-1].replace(",","",100))
                    if item_found == data['item'] and quantity_found == data['prize']:
                        return True			

        try:
            msg: discord.Message = await self.bot.wait_for('message', check=check, timeout=60)
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label=f"Paid at", style=discord.ButtonStyle.url, url=msg.jump_url, emoji="<:tgk_link:1105189183523401828>"))
            embed = message.embeds[0]
            embed.description += f"\n**Payout Location:** {msg.jump_url}"
            embed.description = embed.description.replace("`Initiated`", "`Successfuly Paid`")
            embed.description += f"\n**Santioned By:** {user.mention}"
            embed.title = "Successfully Paid"
            await self.bot.payout_pending.delete(data['_id'])
            await msg.add_reaction("<:tgk_active:1082676793342951475>")
            await asyncio.sleep(random.randint(1, 5))
            await interaction.message.edit(embeds=[embed], view=view)
            is_more_payout_pending = await interaction.client.payout_pending.find_many_by_custom({'winner_message_id': data['winner_message_id']})
            if len(is_more_payout_pending) <= 0:
                loading_emoji = await interaction.client.emoji_server.fetch_emoji(998834454292344842)
                paid_emoji = await interaction.client.emoji_server.fetch_emoji(1052528036043558942)
                winner_channel = interaction.client.get_channel(data['channel'])
                try:
                    winner_message = await winner_channel.fetch_message(data['winner_message_id'])
                    await winner_message.remove_reaction(loading_emoji, interaction.client.user)
                    await winner_message.add_reaction(paid_emoji)
                except Exception as e:
                    pass

        except asyncio.TimeoutError:
            embed = message.embeds[0]
            embed.title = "Payout Queue"
            embed.description = embed.description.replace("`Initiated`", "`Awaiting Payment`")
            view = Payout_Buttton()
            view.children[2].disabled = False
            await interaction.message.edit(embeds=[embed], view=view)
            await message.reply(f"{user.mention} This payout could not be confirmed in time. Please try again, if you think it's a mistake, please contact a `@jay2404`", delete_after=10)

    @commands.Cog.listener()
    async def on_more_pending(self, info: dict):
        data = await self.bot.payout_pending.find_many_by_custom({'winner_message_id': info['_id']})
        if len(data) <= 0:
            loading_emoji = await self.bot.emoji_server.fetch_emoji(998834454292344842)
            paid_emoji = await self.bot.emoji_server.fetch_emoji(1052528036043558942)
            winner_channel = self.bot.get_channel(info['channel'])
            try:
                winner_message = await winner_channel.fetch_message(info['winner_message_id'])
                await winner_message.remove_reaction(loading_emoji, self.bot.user)
                await winner_message.add_reaction(paid_emoji)
            except Exception as e:
                pass
        else:
            return


    @app_commands.command(name="express", description="start doing payouts for the oldest 50 payouts in queue with a single command")
    async def express_payout(self, interaction: discord.Interaction):
        config = await self.bot.payout_config.find(interaction.guild.id)
        if config is None: return
        user_roles = [role.id for role in interaction.user.roles]
        if not (set(user_roles) & set(config['manager_roles'])): 
            await interaction.response.send_message("You don't have permission to use this command", ephemeral=True)
            return
        payouts = await self.bot.payout_pending.find_many_by_custom({'guild': interaction.guild.id})
        if len(payouts) <= 0:
            await interaction.response.send_message("There are no payouts pending", ephemeral=True)
            return
        if config['express'] == True:
            await interaction.response.send_message("There is already a express payout in progress", ephemeral=True)
            return
        payouts = payouts[:50]
        await interaction.response.send_message("## Starting Payouts for oldest 50 payouts in queue", ephemeral=True)
        queue_channel = interaction.guild.get_channel(config['queue_channel'])
        config['express'] = True
        await interaction.client.payout_config.update(config)
        for data in payouts:
            def check(m: discord.Message):
                if m.channel.id != interaction.channel.id: 
                    return False
                if m.author.id != 270904126974590976:
                    if m.author.id == interaction.user.id:
                        if m.content.lower() in ["skip", "next", "pass"]:
                            return True
                    return False
                
                if len(m.embeds) == 0: 
                    return False
                embed = m.embeds[0]
                if embed.description is None or embed.description == "": return False
                if embed.description.startswith("Successfully paid"):

                    found_winner = interaction.guild.get_member(int(embed.description.split(" ")[2].replace("<", "").replace(">", "").replace("!", "").replace("@", ""))) 
                    if data['winner'] != found_winner.id: 
                        return False
                    items = re.findall(r"\*\*(.*?)\*\*", embed.description)[0]
                    if "⏣" in items:
                        items = int(items.replace("⏣", "").replace(",", ""))
                        if items == data['prize']:
                            return True
                        else:
                            return False
                    else:
                        emojis = list(set(re.findall(":\w*:\d*", items)))
                        for emoji in emojis :items = items.replace(emoji,"",100); items = items.replace("<>","",100);items = items.replace("<a>","",100);items = items.replace("  "," ",100)
                        mathc = re.search(r"(\d+)x (.+)", items)
                        item_found = mathc.group(2)
                        quantity_found = int(items.split(" ")[0][:-1].replace(",","",100))
                        if item_found == data['item'] and quantity_found == data['prize']:
                            return True

            embed = discord.Embed(title="Payout Info", description="")
            embed.description += f"**Winner:** <@{data['winner']}>\n"
            if data['item']:
                embed.description += f"**Price:** {data['prize']}x{data['item']}\n"
            else:
                embed.description += f"**Price:** ⏣ {data['prize']:,}\n"
            embed.description += f"**Channel:** <#{data['channel']}>\n"
            embed.description += f"**Host:** <@{data['set_by']}>\n"
            embed.description += f"* Note: To skip this payout, type `skip`, `next` or `pass`"
            cmd = ""
            if not data['item']:
                cmd += f"/serverevents payout user:{data['winner']} quantity:{data['prize']}"
            else:
                cmd += f"/serverevents payout user:{data['winner']} quantity:{data['prize']} item:{data['item']}"
            embed.add_field(name="Command", value=f"{cmd}")
            embed.set_footer(text=f"Queue Number: {payouts.index(data)+1}/{len(payouts)}")
            await asyncio.sleep(1.25)
            link_view = discord.ui.View()
            link_view.add_item(discord.ui.Button(label=f"Queue Link", style=discord.ButtonStyle.url, url=f"https://discord.com/channels/{interaction.guild.id}/{queue_channel.id}/{data['_id']}", emoji="<:tgk_link:1105189183523401828>"))
            await interaction.followup.send(embed=embed, ephemeral=True, view=link_view)
            try:
                msg: discord.Message = await self.bot.wait_for('message', check=check, timeout=60)
                if msg.author.id == interaction.user.id:
                    if msg.content.lower() in ["skip", "next", "pass"]:
                        await interaction.followup.send("Skipping...", ephemeral=True)
                        await msg.delete()
                        continue

                view = discord.ui.View()
                view.add_item(discord.ui.Button(label=f"Paid at", style=discord.ButtonStyle.url, url=msg.jump_url, emoji="<:tgk_link:1105189183523401828>"))
                try:
                    winner_message = await queue_channel.fetch_message(data['_id'])
                except discord.NotFound:
                    continue
                embed = winner_message.embeds[0]
                embed.description += f"\n**Payout Location:** {msg.jump_url}"
                embed.description = embed.description.replace("`Awaiting Payment`", "`Successfuly Paid`")
                embed.description = embed.description.replace("`Initiated`", "`Successfuly Paid`")
                embed.title = "Successfully Paid"
                await self.bot.payout_pending.delete(data['_id'])
                await msg.add_reaction("<:tgk_active:1082676793342951475>")
                await winner_message.edit(embed=embed, view=view, content=None)
                self.bot.dispatch("more_pending", data)
                if not data['item']:
                    interaction.client.dispatch("payout_paid", msg, interaction.user, interaction.guild.get_member(data['winner']), data['prize'])
                else:
                    interaction.client.dispatch("payout_paid", msg, interaction.user, interaction.guild.get_member(data['winner']), f"{data['prize']}x{data['item']}")
                continue

            except asyncio.TimeoutError:
                config['express'] = False
                await interaction.client.payout_config.update(config)
                await interaction.followup.send("Timed out you can try command again", ephemeral=True)
                return
        
        config['express'] = False
        await interaction.client.payout_config.update(config)
        await interaction.followup.send("Finished Express Payout", ephemeral=True)

utc = datetime.timezone.utc
time = datetime.time(hour=4, minute=30, tzinfo=utc)

class donation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db2 = bot.aceDb["TGK"]
        self.bot.donorBank = Document(self.db2, "donorBank")
        self.grinder_reminder.start()
        self.celeb_lb.start()

    def cog_unload(self):
        self.grinder_reminder.cancel()
        self.celeb_lb.cancel()

    # for grinders reminder
    @tasks.loop(time=time)
    async def grinder_reminder(self):

        gk: discord.Guild = self.bot.get_guild(785839283847954433)
        grinder = gk.get_role(836228842397106176)
        trial = gk.get_role(932149422719107102)
        mythic = gk.get_role(835866409992716289)
        legendary = gk.get_role(806804472700600400)

        grinder_channel = self.bot.get_channel(851663580620521472)
        log_channel = self.bot.get_channel(1119998681924509747)

        members = grinder.members
        members.extend(trial.members)

        records = await self.bot.donorBank.find_many_by_custom( {"grinder_record" : {"$exists":"true"}})
        data = {}
        for record in records:
            data[str(record['_id'])] = record['grinder_record']

        # get current time
        date = datetime.date.today()
        current_time = datetime.datetime(date.year, date.month, date.day) + datetime.timedelta(days=0)

        for member in members:
            record = data[str(member.id)]
            if record['time'] == current_time:
                time_diff = 0
            else:
                time_diff = int(str(record['time'] - current_time).split(" ")[0])

            content = ''
            if time_diff <= 0:
                message_for_pending = ""
                if time_diff < -1:
                    message_for_pending += f"> **Pending from:** {-time_diff} days!\n\n"
                elif time_diff == -1:
                    message_for_pending += f"> **Pending from:** {-time_diff} day!\n\n"
                elif time_diff == 0:
                    message_for_pending += f"> **Donation is due today!\n\n"
                else:
                    message_for_pending += f"> **Due in:** {time_diff} days!\n\n"
                payment_pending = discord.Embed(
                    title=f"<a:TGK_Pandaswag:830525027341565982>  __TGK's Grinders Team__  <a:TGK_Pandaswag:830525027341565982>\n\n",
                    description=f" <:tgk_redarrow:1005361235715424296> Your grinder donations are pending for **{-time_diff+1} days**. \n"
                                f" <:tgk_redarrow:1005361235715424296> Please send `⏣ {(int(-time_diff+1)*record['amount_per_grind']):,}` in <#851663580620521472> today. \n"
                                f" <:tgk_redarrow:1005361235715424296> Inform staff if you have any trouble with donations.  \n",
                    colour=discord.Color.random(),
                    timestamp=datetime.datetime.now()
                )
                payment_pending.set_footer(text=f"Developed by utki007 & Jay",
                                           icon_url=gk.icon.url)
                try:
                    await member.send(content=f"Hello {member.name}! I have a message for you:", embed=payment_pending)
                except:
                    await grinder_channel.send(content=f"Hello {member.mention}! I have a message for you:", embed=payment_pending)
                
                # await log_channel.send(content=f"Sent {member.mention} the following message:", embed=payment_pending, allowed_mentions=discord.AllowedMentions(users=False, everyone=False,roles=False))
                
                try:
                    pending_from = -time_diff + 1
                    msg = ''
                    flag = 0
                    if pending_from >= 3 and pending_from < 6:
                        if grinder in member.roles:
                            await member.remove_roles(grinder)
                            msg += f"- **Removed:** {grinder.mention}\n"
                            flag = 1
                        if trial not in member.roles:
                            await member.add_roles(trial)
                            msg += f"- **Added:** {trial.mention}\n"
                            flag = 1
                        if flag == 1:
                            title = f'Demoted {member.name}!'
                        else:
                            continue
                    elif pending_from >= 6:
                        if grinder in member.roles:
                            await member.remove_roles(grinder)
                            msg += f"- **Removed:** {grinder.mention}\n"
                            flag = 1
                        if trial in member.roles:
                            await member.remove_roles(trial)
                            msg += f"- **Removed:** {trial.mention}\n"
                            flag = 1
                        if mythic in member.roles:
                            await member.remove_roles(mythic)
                            msg += f"- **Removed:** {mythic.mention}\n"
                            flag = 1
                        if legendary in member.roles:
                            await member.remove_roles(legendary)
                            msg += f"- **Removed:** {legendary.mention}\n"
                            flag = 1
                        if flag == 1:
                            title = f'Kicked {member.name}!'
                        else:
                            continue
                    else:
                        continue
                except:
                    msg = f"- **Error:** Unable to remove roles for {member.mention}\n"
                
                try:
                    payment_pending.title = title
                    payment_pending.description = msg
                    payment_pending.set_thumbnail(url=member.avatar.url)
                    # payment_pending.set_author(name=member.name, icon_url=member.avatar.url)
                    payment_pending.set_footer(text=f'ID: {member.id}')	
                    await log_channel.send(embed=payment_pending)	
                except:
                    pass						

                await asyncio.sleep(0.5)
    
    @grinder_reminder.error
    async def grinder_reminder_error(self, error):
        chal = self.bot.get_channel(999555462674522202)
        await chal.send(f"<@488614633670967307> <@301657045248114690> ,Error in grinder reminder: {error}")

    @grinder_reminder.before_loop
    async def before_grinder_reminder(self):
        await self.bot.wait_until_ready()
    
    @tasks.loop(time=time)
    async def celeb_lb(self):
        gk = self.bot.get_guild(785839283847954433)
        leaderboard_channel = gk.get_channel(1209873854369898506)
        log_channel = gk.get_channel(1074276583940034581)
        beast_role = gk.get_role(821052747268358184)
        members = beast_role.members

        if leaderboard_channel is None: 
            return

        data = await self.bot.donorBank.find_many_by_custom( {"event" : { "$elemMatch": { "name": '10k',"bal":{"$gt":0} }}})
        df = pd.DataFrame(data)
        df['10k']  = df.event.apply(lambda x: x[-1]['bal'])
        df = df.drop(['bal','grinder_record','event'], axis=1)
        df = df.sort_values(by='10k',ascending=False)
        top_3 = df.head(3)
        top_10 = df.head(10)

        message = [message async for message in leaderboard_channel.history(limit=1)][0]
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Check Leaderboard", style=discord.ButtonStyle.url, url=message.jump_url, emoji="<:tgk_link:1105189183523401828>"))
                

        for user in beast_role.members:
            if user.id not in top_3['_id'].values:
                await user.remove_roles(beast_role)
                embed = discord.Embed(
                    title="You dropped from top 3!",
                    description= f"Your `{beast_role.name}` role has been removed.\n"
                                f"Don't worry, you can always grind your way back up!",
                    color=0x2b2d31
                )
                embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/830548561329782815.gif?v=1")
                embed.set_footer(text=f"{gk.name}", icon_url=gk.icon.url)
                try:
                    await user.send(embed=embed, view=view)
                    await log_channel.send(f'Removed {beast_role.mention} from {user.mention}(`{user.id}`).', allowed_mentions=discord.AllowedMentions.none())
                except:
                    await log_channel.send(f'Removed {beast_role.mention} from {user.mention}(`{user.id}`).\n> **Error:** Unable to send DM to user.', allowed_mentions=discord.AllowedMentions.none())
                await asyncio.sleep(1)

        leaderboard = []
        users = []
        for index in top_10.index:
            user = gk.get_member(top_10['_id'][index])
            users.append(user)
            leaderboard.append({'user': user,'name': top_10['name'][index],'donated': top_10['10k'][index]}) 
            if beast_role not in user.roles:
                await user.add_roles(beast_role)
                embed = discord.Embed(
                    title="You made it to top 3!",
                    description=f"Congrats! Keep it up and grind your way to the top!",
                    color=0x2b2d31
                )
                embed.add_field(name="You received:", value=f"`{beast_role.name}` role", inline=False)
                embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/830519601384128523.gif?v=1")
                embed.set_footer(text=f"{gk.name}", icon_url=gk.icon.url)
                try:
                    await user.send(embed=embed, view=view)
                    await log_channel.send(f'Added {beast_role.mention} to {user.mention}(`{user.id}`).', allowed_mentions=discord.AllowedMentions.none())
                except:
                    await log_channel.send(f'Added {beast_role.mention} to {user.mention}(`{user.id}`).\n> **Error:** Unable to send DM to user.', allowed_mentions=discord.AllowedMentions.none())
                await asyncio.sleep(1)
        
        image = await self.create_lb(gk, leaderboard)
        

        with BytesIO() as image_binary:
            image.save(image_binary, 'PNG')
            image_binary.seek(0)
            await leaderboard_channel.send(file=discord.File(fp=image_binary, filename=f'{gk.name}_celeb_lb_card.png'))
            image_binary.close()
        
    @celeb_lb.before_loop
    async def before_celeb_lb(self):
        await self.bot.wait_until_ready()
    
    # async def round_pfp(self, pfp: discord.User | discord.Guild | discord.User):
    #     if isinstance(pfp, discord.Member) or isinstance(pfp, discord.User):
    #         if pfp.avatar is None:
    #             pfp = pfp.default_avatar.with_format('png')
    #         else:
    #             pfp = pfp.avatar.with_format('png')
    #     else:
    #             pfp = pfp.icon.with_format('png')

    #     pfp = BytesIO(await pfp.read())
    #     pfp = Image.open(pfp)
    #     pfp = pfp.resize((95, 95), Image.Resampling.LANCZOS).convert('RGBA')

    #     bigzise = (pfp.size[0] * 3, pfp.size[1] * 3)
    #     mask = Image.new('L', bigzise, 0)
    #     draw = ImageDraw.Draw(mask)
    #     draw.ellipse((0, 0) + bigzise, fill=255)
    #     mask = mask.resize(pfp.size, Image.Resampling.LANCZOS)
    #     mask = ImageChops.darker(mask, pfp.split()[-1])
    #     pfp.putalpha(mask)

    #     return pfp

    # async def create_winner_card(self, guild: discord.Guild, event_name:str, data: list):
    #     template = Image.open('./assets/leaderboard_template.png')
    #     guild_icon = await self.round_pfp(guild)
    #     template.paste(guild_icon, (15, 8), guild_icon)

    #     draw = ImageDraw.Draw(template)
    #     font = ImageFont.truetype('./assets/fonts/DejaVuSans.ttf', 24)
    #     winner_name_font = ImageFont.truetype('./assets/fonts/Symbola.ttf', 28)
    #     winner_exp_font = ImageFont.truetype('./assets/fonts/DejaVuSans.ttf', 20)

    #     winne_postions = {
    #         #postions of the winners, pfp and name and donation
    #         0: {'icon': (58, 150), 'name': (176, 165), 'donated': (176, 202)},
    #         1: {'icon': (58, 265), 'name': (176, 273), 'donated': (176, 309)},
    #         2: {'icon': (58, 380), 'name': (176, 392), 'donated': (176, 428)}}

    #     draw.text((135, 28), f"{event_name}", font=winner_name_font, fill="#9A9BD5") #guild name 
    #     draw.text((135, 61), f"Gambler's Kingdom", font=font, fill="#9A9BD5") #event name

    #     for i in data[:3]:
    #         user = i['user']
    #         index = data.index(i)
    #         user_icon = await self.round_pfp(user)
    #         template.paste(user_icon, winne_postions[index]['icon'], user_icon)
    #         draw.text(winne_postions[index]['name'], f"👑 | {i['name']}", font=winner_name_font, fill="#9A9BD5")
    #         draw.text(winne_postions[index]['donated'], f"⏣ {i['donated']:,}", font=winner_exp_font, fill="#A8A8C8")

    #     return template
 
    async def round_pfp(self, pfp: discord.Member | discord.Guild, size: tuple = (124, 124)):
        if isinstance(pfp, discord.Member):
            if pfp.avatar is None:
                pfp = pfp.default_avatar.with_format("png")
            else:
                pfp = pfp.avatar.with_format("png")
        else:
            pfp = pfp.icon.with_format("png")

        pfp = BytesIO(await pfp.read())
        pfp = Image.open(pfp)
        pfp = pfp.resize(size, Image.Resampling.LANCZOS).convert('RGBA')
        
        bigzise = (pfp.size[0] * 3, pfp.size[1] * 3)
        mask = Image.new('L', bigzise, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + bigzise, fill=255)
        mask = mask.resize(pfp.size, Image.Resampling.LANCZOS)
        mask = ImageChops.darker(mask, pfp.split()[-1])
        pfp.putalpha(mask)

        return pfp    

    async def create_lb(self, guild: discord.Guild, data: dict):
        image = Image.open("./assets/10k_lb.png")
        crown = Image.open("./assets/crown.png")
        draw = ImageDraw.Draw(image)

        
        image.paste(crown, (165, 65), crown)

        winner_postions = {
            #postions of the winners, pfp and name and donation
            0: {'icon': (160, 90), 'name': (150, 145), 'donated': (150, 165)},
            1: {'icon': (50, 100), 'name': (45, 150), 'donated': (45, 170)},
            2: {'icon': (280, 100), 'name': (275, 150), 'donated': (275, 170)},
            3: {'icon': (60, 207), 'name': (100, 212), 'donated': (220, 212)},
            4: {'icon': (60, 240), 'name': (100, 245), 'donated': (220, 245)},
            5: {'icon': (60, 273), 'name': (100, 278), 'donated': (220, 278)},
            6: {'icon': (60, 306), 'name': (100, 311), 'donated': (220, 311)},
            7: {'icon': (60, 339), 'name': (100, 344), 'donated': (220, 344)},
            8: {'icon': (60, 372), 'name': (100, 377), 'donated': (220, 377)},
            9: {'icon': (60, 405), 'name': (100, 410), 'donated': (220, 410)} 
        }

        for winner in data:
            user = winner['user']
            index = data.index(winner)
            if index == 0:
                pfp = await self.round_pfp(user, (50, 50))
            elif index in [1,2]:
                pfp = await self.round_pfp(user, (44, 44))
            else:
                pfp = await self.round_pfp(user, (25,25))
            image.paste(pfp, winner_postions[index]['icon'], pfp)
            if index == 0:
                draw.text(winner_postions[index]['name'], f"👑 | {winner['name'][:8]}", font=ImageFont.truetype("./assets/fonts/Symbola.ttf", 16), fill=(254, 205, 61))
                draw.text(winner_postions[index]['donated'], f"⏣ {millify(winner['donated'])}", font=ImageFont.truetype("./assets/fonts/DejaVuSans.ttf", 16), fill=(80, 200, 120))
            elif index in [1,2]:
                draw.text(winner_postions[index]['name'], f"👑 | {winner['name']}", font=ImageFont.truetype("./assets/fonts/Symbola.ttf", 14), fill=(254, 205, 61))
                draw.text(winner_postions[index]['donated'], f"⏣ {millify(winner['donated'])}", font=ImageFont.truetype("./assets/fonts/DejaVuSans.ttf", 14), fill=(80, 200, 120))
            else:
                draw.text(winner_postions[index]['name'], f"{winner['name'][:13]}", font=ImageFont.truetype("./assets/fonts/Symbola.ttf", 14), fill=(0,174,255))
                draw.text(winner_postions[index]['donated'], f"⏣ {(winner['donated']):,}", font=ImageFont.truetype("./assets/fonts/DejaVuSans.ttf", 12), fill=(80, 200, 120))
            
        return image
    
    @app_commands.command(name="celeb-lb", description="Celeb Leaderboard 📈")
    async def _leaderboard(self, interaction: discord.Interaction):
        if interaction.user.id not in  [488614633670967307,301657045248114690]:
            return await interaction.response.send_message("Work in progress, try again later!", ephemeral=True)
        await interaction.response.defer(thinking=True, ephemeral=False)

        data = await self.bot.donorBank.find_many_by_custom( {"event" : { "$elemMatch": { "name": '10k',"bal":{"$gt":0} }}})
        df = pd.DataFrame(data)
        df['10k']  = df.event.apply(lambda x: x[-1]['bal'])
        df = df.drop(['bal','grinder_record','event'], axis=1)
        df = df.sort_values(by='10k',ascending=False)
        top_10 = df.head(10)

        leaderboard = []
        for index in top_10.index:
            user = interaction.guild.get_member(top_10['_id'][index])
            leaderboard.append({'user': user,'name': top_10['name'][index],'donated': top_10['10k'][index]}) 
        
        # image = await self.create_winner_card(interaction.guild, "🎊 10K Celeb's LB 🎊", leaderboard)
        image = await self.create_lb(interaction.guild, leaderboard)

        with BytesIO() as image_binary:
            image.save(image_binary, 'PNG')
            image_binary.seek(0)
            await interaction.followup.send(file=discord.File(fp=image_binary, filename=f'{interaction.guild.name}_celeb_lb_card.png'))
            image_binary.close()


class Seggestions_db:
    def __init__(self, bot):
        self.db = bot.mongo['Suggestion']
        self.config = Document(self.db, 'config')
        self.suggestions = Document(self.db, 'suggestions')


class Suggestions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.suggestions = Seggestions_db(bot)

    
    @commands.command(name="suggest", description="Suggest something for the server")
    @commands.has_any_role(785842380565774368, 785845265118265376, 818129661325869058)
    async def _suggest(self, ctx: commands.Context, *, suggestion: str):
        config = await self.suggestions.config.find(ctx.guild.id)
        if config is None:
            return await ctx.send("Suggestions are disabled in this server")
        if config['channel'] is None:
            return await ctx.send("Suggestions are disabled in this server")
        channel = ctx.guild.get_channel(config['channel'])
        if channel is None:
            return await ctx.send("Suggestions are disabled in this server")
        
        embed = discord.Embed(title=f"Suggestion #{config['count']}", description=suggestion, color=discord.Color.blurple())
        embed.set_author(name=ctx.author, icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar)
        embed.set_footer(text=f"ID: {ctx.author.id}")
        msg = await channel.send(embed=embed)
        await msg.add_reaction('<a:ace_upvote:1004650954118942812>')
        await msg.add_reaction('<a:ace_downvote:1004651017427755058>')
        data = {
            '_id': config['count'],
            'author': ctx.author.id,
            'channel': channel.id,
            'message': msg.id,
            'suggestion': suggestion,
            'status': 'pending'
        }
        await self.suggestions.suggestions.insert(data)
        config['count'] += 1
        await self.suggestions.config.update(config)

        await ctx.send("Suggestion sent successfully")
        await ctx.message.delete()
        await msg.create_thread(name=f"Suggestion #{config['count']}", auto_archive_duration=1440)

    @commands.command(name="deny", description="Deny a suggestion")
    @commands.has_permissions(manage_guild=True)
    async def _deny(self, ctx: commands.Context, id: int, *, reason: str):

        data = await self.suggestions.suggestions.find(id)
        if data is None:
            return await ctx.send("Invalid suggestion id")
        if data['status'] != 'pending':
            return await ctx.send("This suggestion is already processed")
        
        channel = ctx.guild.get_channel(data['channel'])
        if channel is None:
            return await ctx.send("Invalid suggestion id")
        try:
            msg = await channel.fetch_message(data['message'])
        except discord.NotFound:
            return await ctx.send("Invalid suggestion id")
        
        embed = msg.embeds[0]
        embed.color = discord.Color.red()
        embed.title += " (Denied)"
        embed.add_field(name=f"Reason by {ctx.author.name}", value=reason)

        await msg.edit(embed=embed)
        data['status'] = 'denied'
        await self.suggestions.suggestions.update(data)
        await ctx.send("Suggestion denied successfully")

        author = ctx.guild.get_member(data['author'])
        try:
            await author.send(f"Your suggestion `{data['suggestion']}` was denied by {ctx.author.name} for the following reason:\n{reason}")
        except discord.Forbidden:
            pass

    @commands.command(name="accept", description="Accept a suggestion")
    @commands.has_permissions(manage_guild=True)
    async def _accept(self, ctx: commands.Context, id: int, *, reason: str):
        
        data = await self.suggestions.suggestions.find(id)
        if data is None:
            return await ctx.send("Invalid suggestion id")
        if data['status'] != 'pending':
            return await ctx.send("This suggestion is already processed")
        
        channel = ctx.guild.get_channel(data['channel'])
        if channel is None:
            return await ctx.send("Invalid suggestion id")
        try:
            msg = await channel.fetch_message(data['message'])
        except discord.NotFound:
            return await ctx.send("Invalid suggestion id")
        
        embed = msg.embeds[0]
        embed.color = discord.Color.green()
        embed.title += " (Accepted)"
        embed.add_field(name=f"Reason by {ctx.author.name}", value=reason)

        await msg.edit(embed=embed)
        data['status'] = 'accepted'
        await self.suggestions.suggestions.update(data)
        await ctx.send("Suggestion accepted successfully")

        author = ctx.guild.get_member(data['author'])
        if author is None:
            return
        try:
            await author.send(f"Your #{data['_id']} suggestion has been accepted by {ctx.author.name}.\nReason: {reason}")
        except discord.Forbidden:
            pass
    
    @commands.command(name="suggestion-channel", description="Set the suggestion channel", aliases=['suggestc'])
    @commands.has_permissions(administrator=True)
    async def _suggestion_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        config = await self.suggestions.config.find(ctx.guild.id)
        if config is None:
            config = {
                '_id': ctx.guild.id,
                'channel': None,
                'count': 1
            }
        config['channel'] = channel.id
        await self.suggestions.config.update(config)
        await ctx.send(f"Suggestion channel set to {channel.mention}")

async def setup(bot):
    await bot.add_cog(Payout(bot))
    await bot.add_cog(Suggestions(bot))
    await bot.add_cog(
        donation(bot),
        guilds = [discord.Object(785839283847954433)]
    )
