import discord
import asyncio
import re
from discord.ext import commands
from discord import app_commands, Interaction
from utils.db import Document
from typing import List, Dict, TypedDict
from utils.transformer import DMCConverter
from utils.paginator import Paginator
from utils.views.request_system import Event_view

class Event(TypedDict):
    name: str
    min_amount: int

class Config(TypedDict):
    _id: int
    events: Dict[str, Event]
    request_channel: int | None
    request_queue: int | None
    manager_roles: List[int]

class Request_dv:
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.mongo["Events"]
        self.request = Document(self.db, "request")
        self.config = Document(self.db, "config")
        self.config_cache: dict[int, Config] = {}

    async def setup(self):
        for guild in await self.config.get_all():
            self.config_cache[guild["_id"]] = guild

    async def get_config(self, guild_id: int) -> Config:
        if guild_id in self.config_cache:
            return self.config_cache[guild_id]
        else:
            config: Config = await self.config.find(guild_id)
            if config is None:
                config: Config = {'_id': guild_id, 'events': {}, 'request_channel': None, 'request_queue': None,
                                  'manager_roles': [], 'event_channel': None}
                await self.config.insert(config)
            self.config_cache[guild_id] = config
            return config
    
    async def update_config(self, data: Config):
        await self.config.update(data)
        self.config_cache[data["_id"]] = data
        return data
    
    async def verfiy_donation(self, user: discord.Member, thread: discord.Thread, quantity: int, item: str=None) -> bool:
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
            if not item:
                items = items.replace("⏣", "").replace(",", "").replace(" ", "")
                items = int(items)
                if items == quantity:
                    return True
                else:
                    return False
            emojis = list(set(re.findall(":\w*:\d*", items)))
            for emoji in emojis: items = items.replace(emoji, "", 100); items = items.replace("<>", "",
                                                                                              100);items = items.replace(
                "<a>", "", 100);items = items.replace("  ", " ", 100)
            mathc = re.search(r"(\d+)x (.+)", items)
            item_found = mathc.group(2)
            quantity_found = int(mathc.group(1))
            if item.lower() == item_found.lower() and quantity == quantity_found:
                return True
            else:
                return False
        except asyncio.TimeoutError:
            return False


class Event(commands.GroupCog, name="event"):
    def __init__(self, bot):
        self.bot = bot
        self.backend = Request_dv(bot)
        self.bot.events = self.backend

    async def event_autocomplete(self, interaction: Interaction, current: str) -> List[app_commands.Choice[str]]:
        guild = self.backend.config_cache[interaction.guild_id]
        if not guild:
            return [
                app_commands.Choice(name="No events found", value="No events found")
            ]
        events = guild["events"]
        return [
            app_commands.Choice(name=event["name"], value=event["name"])
            for event in events.values() if current.lower() in event["name"].lower()
        ]

    async def item_autocomplete(self, interaction: discord.Interaction, string: str) -> List[app_commands.Choice[str]]:
        choices: list[app_commands.Choice[str]] = []
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

    @commands.Cog.listener()
    async def on_ready(self):
        await self.backend.setup()
        self.bot.add_view(Event_view())

    @app_commands.command(name="request", description="Request an event")
    @app_commands.autocomplete(event=event_autocomplete, item=item_autocomplete)
    async def _request(self, interaction: Interaction, event: str, amount: app_commands.Transform[int, DMCConverter],
                    item: str = None, host_message: str = None, requirements: str = None):
        config: Config = await self.backend.get_config(interaction.guild_id)
        if not config["request_channel"]:
            await interaction.response.send_message("No request channel set", ephemeral=True)
            return
        if not config["request_queue"]:
            await interaction.response.send_message("No request queue set", ephemeral=True)
            return
        if interaction.channel.id != config["request_channel"]:
            await interaction.response.send_message(f"You can only use this command in the request channel <#{config['request_channel']}>", ephemeral=True)
            return
        if event not in config["events"].keys():
            await interaction.response.send_message("Invalid event", ephemeral=True)
            return
        embed = discord.Embed(color=interaction.client.default_color, description="")
        embed.description += f"**Requested By:** {interaction.user.mention}\n"
        embed.description += f"**Event:** {event}\n"
        if item:
            embed.description += f"**Price**: `{amount}x`{item}\n"
        else:
            
            if amount < config["events"][event]["min_amount"]:
                await interaction.response.send_message(f"Minimum amount is {config['events'][event]['min_amount']}", ephemeral=True)
                return

            embed.description += f"**Price**: ⏣ {amount:,}\n"
        if host_message:
            embed.description += f"**Message:** {host_message}\n"
        if requirements:
            embed.description += f"**Requirements:** {requirements}\n"
        await interaction.response.send_message(embed=embed, ephemeral=False)
        message = await interaction.original_response()
        data: dict = {
            "_id": message.id,
            "event": event,
            "amount": amount,
            "item": item if item else None,
            "message": host_message if host_message else None,
            "requirements": requirements if requirements else None,
            "user": interaction.user.id,
            "guild": interaction.guild_id,
            "queue_id": None
        }
        thread: discord.Thread = await message.create_thread(name="Donation Verification", auto_archive_duration=1440)
        data["thread"] = thread.id
        try:await thread.add_user(interaction.user)
        except Exception:pass
        if item:
            await thread.send(f"/serverevents donate quantity:{amount} item:{item}")
        else:
            await thread.send(f"/serverevents donate quantity:{amount}")

        donated = await self.backend.verfiy_donation(interaction.user, thread, amount, item if item else None)
        if not donated:
            await thread.send(f"{interaction.user.mention} did not provide the correct donation/have not donated within 5 minutes")
            await thread.edit(locked=True, archived=True)
            return
        
        await thread.send(f"{interaction.user.mention} your event request has been received and will be processed shortly")
        await thread.edit(auto_archive_duration=60, name="Donation Verified")
        await self.backend.request.insert(data)
        queue_embed = discord.Embed(color=interaction.client.default_color, description="")
        queue_embed.set_author(name=f"{data['event']} Request")
        queue_embed.description += f"**Requested By:** {interaction.user.mention}\n"
        if item:
            queue_embed.description += f"**Price**: `{amount}x` {item}\n"
        else:
            queue_embed.description += f"**Price**: ⏣ {amount:,}\n"
        if host_message:
            queue_embed.description += f"**Message:** {host_message}\n"
        if requirements:
            queue_embed.description += f"**Requirements:** {requirements}\n"
        
        queue_embed.description += f"**Status:** Pending\n"
        
        queue_channel = interaction.guild.get_channel(config["request_queue"])
        view = Event_view()
        view.add_item(discord.ui.Button(label="Donated At", emoji="<:tgk_link:1105189183523401828>", url=f"https://canary.discord.com/channels/{interaction.guild.id}/{thread.id}", style=discord.ButtonStyle.link))
        queue_message = await queue_channel.send(embed=queue_embed, view=view)
        data['queue_id'] = queue_message.id
        await self.backend.request.update(data)


    @app_commands.command(name="start", description="Start an event")
    @app_commands.autocomplete(event=event_autocomplete)
    async def _start(self, interaction: Interaction, event: str):
        config = await self.backend.get_config(interaction.guild_id)
        user_roles = [role.id for role in interaction.user.roles]
        if not (set(user_roles) & set(config['manager_roles'])):
            return await interaction.response.send_message("You are not allowed to use this command!", ephemeral=True)
        
        oldest_pending_event = await self.backend.request.find_many_by_custom({
            'event': event, 'guild': interaction.guild_id
        })
        if len(oldest_pending_event) == 0:
            return await interaction.response.send_message("No pending events", ephemeral=True)
        pages = []
        for data in oldest_pending_event:
            embed = discord.Embed(color=interaction.client.default_color, description="")
            embed.description += f"**Requested By:** <@{data['user']}>\n"
            if data['item']:
                embed.description += f"**Price**: `{data['amount']}x` {data['item']}\n"
            else:
                embed.description += f"**Price**: ⏣ {data['amount']:,}\n"
            if data['message']:
                embed.description += f"**Message:** {data['message']}\n"
            if data['requirements']:
                embed.description += f"**Requirements:** {data['requirements']}\n"
            embed.description += f"**Donated At:** [Click Here](https://canary.discord.com/channels/{interaction.guild_id}/{data['thread']})\n"
            pages.append(embed)

        await Paginator(interaction, pages).start(embeded=True, quick_navigation=False, hidden=True)

async def setup(bot):
    await bot.add_cog(Event(bot))
