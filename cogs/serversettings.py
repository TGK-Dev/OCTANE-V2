import discord
from discord.ext import commands
from discord import app_commands
from discord.app_commands import Group
from typing import Literal
from utils.db import Document
from utils.views.JoinGateSettings_system import JoinGateSettings_Edit
from utils.views.payout_system import Payout_Config_Edit
from utils.views.ticket_system import Config_Edit as Ticket_Config_Edit
from utils.views.staff_system import Staff_config_edit
from utils.views.level_system import LevelingConfig
from modules.perks.views import PerkConfig
from utils.views.auction import AuctionConfig
from utils.views.giveaway import GiveawayConfig
from utils.views.blacklist import Blacklist_Config
from utils.views import request_system
import humanfriendly
import unicodedata
import unidecode
import stringcase
import re
import datetime

class serversettingsDB():
    def __init__(self, bot, Document):
        self.bot = bot
        self.join_gate = Document(bot.db, "join_gate")
        self.starboard = Document(bot.db, "starboard")
    
    async def get_config(self, settings, guild_id):
        match settings:
            case "join_gate":
                config = await self.join_gate.find(guild_id)
                if config is None: 
                    config = await self.create_config('join_gate', guild_id)
                return config
            case "starboard":
                config = await self.starboard.find(guild_id)
                if config is None: config = await self.create_config(guild_id)
                return config
    
    async def create_config(self, settings, guild_id):
        match settings:
            case "join_gate":
                config = {"_id": guild_id, "joingate": {'enabled': None, 'action': None, 'accountage': None, 'whitelist': [], 'autorole': [], 'decancer': None, 'logchannel': None}}
                await self.join_gate.insert(config)
                return config


    async def update_config(self, settings, guild_id, config):
        match settings:
            case "join_gate":
                await self.join_gate.update(guild_id, config)

class serversettings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.ss = serversettingsDB(bot, Document)
    
    settings = [
        app_commands.Choice(name="Auctions", value="auctions"),
        app_commands.Choice(name="Blacklist", value="blacklist"),
        app_commands.Choice(name="Event Request System", value="events"),
        app_commands.Choice(name="Giveaways", value="giveaways"),
        app_commands.Choice(name="Join Verification", value="join_gate"),
        app_commands.Choice(name="Leveling System", value="leveling"),
        app_commands.Choice(name="Perks System", value="perks"),
        app_commands.Choice(name="Payout System", value="payout"),
        app_commands.Choice(name="Staff Managment", value="staff"),
        app_commands.Choice(name="Tickets System", value="tickets"),        
    ]
    
    @app_commands.command(name="serversettings", description="Change the settings of the server")
    @app_commands.choices(settings=settings)
    @app_commands.describe(option="Show or edit the settings", settings="The settings you want to change")
    @app_commands.default_permissions(administrator=True)
    async def serversettings(self, interaction: discord.Interaction, settings: app_commands.Choice[str], option: Literal['Show', 'Edit']):
        if interaction.client.user.id == 816699167824281621:
            if interaction.guild.id != 785839283847954433:
                if settings.value not in ["payout", "perks", "staff", "tickets"]:
                    return await interaction.response.send_message("This command is not available for this server", ephemeral=True)
        
        match settings.value:
            case "join_gate":
                config = await self.bot.ss.get_config(settings.value, interaction.guild_id)
                embed = discord.Embed(title="Join Gate Settings", description="", color=0x2b2d31)
                embed.description += f"**Enabled:** `{config['joingate']['enabled']}`\n"
                embed.description += f"**Decancer:** `{config['joingate']['decancer'] if config['joingate']['decancer'] is not None else 'None'}`\n"
                embed.description += f"**Action:** `{config['joingate']['action'] if config['joingate']['action'] is not None else 'None'}`\n"
                embed.description += f"**Account Age:** `{str(config['joingate']['accountage']) +('Days') if config['joingate']['accountage'] is not None else 'None'}`\n"
                embed.description += f"**Whitelist:** {','.join([f'<@{user}>' for user in config['joingate']['whitelist']]) if len(config['joingate']['whitelist']) > 0 else '`None`'}\n"
                embed.description += f"**Auto Role:** {','.join([f'<@&{role}>' for role in config['joingate']['autorole']]) if len(config['joingate']['autorole']) > 0 else '`None`'}\n"
                embed.description += f"**Log Channel:** {interaction.guild.get_channel(config['joingate']['logchannel']).mention if config['joingate']['logchannel'] is not None else '`None`'}\n"

                if option == "Show":
                    await interaction.response.send_message(embed=embed)
                elif option == "Edit":
                    view = JoinGateSettings_Edit(interaction, config)
                    await interaction.response.send_message(embed=embed, view=view)
                    view.message = await interaction.original_response()
                    await view.wait()
                    if view.value:
                        await self.bot.ss.update_config(settings.value, interaction.guild_id, view.data)

            case "staff":
                guild_config = await self.bot.staff_db.get_config(interaction.guild.id)
                if interaction.user.id != interaction.guild.owner.id and interaction.user.id not in guild_config['owners']:
                    return await interaction.response.send_message("You are not allowed to use this command!", ephemeral=True)
                
                embed = discord.Embed(title=f"{interaction.guild.name}'s Staff Settings", description="")
                embed.description += f"**Owners:** {', '.join([f'<@{owner}>' for owner in guild_config['owners']])}\n"
                embed.description += f"**Staff Managers:** {', '.join([f'<@{role}>' for role in guild_config['staff_manager']])}\n"
                embed.description += f"**Base Role:**" + (f" <@&{guild_config['base_role']}>" if guild_config['base_role'] != None else "`None`") + "\n"
                embed.description += f"**Leave Role:**" + (f" <@&{guild_config['leave_role']}>" if guild_config['leave_role'] != None else "`None`") + "\n"        
                embed.description += f"**Leave Channel:**" + (f" <#{guild_config['leave_channel']}>" if guild_config['leave_channel'] != None else "`None`") + "\n"
                embed.description += f"**Logging Channel:**" + (' **Webhook setup done**' if guild_config['webhook_url'] != None else "`None`") + "\n"
                embed.description += f"**Max Positions:** {guild_config['max_positions']}\n"
                embed.description += f"**Last Edit:** <t:{round(guild_config['last_edit'].timestamp())}:R>\n"
                embed.description += f"**Positions:** {', '.join([f'`{position.capitalize()}`' for position in guild_config['positions'].keys()])}\n"

                if option == "Show":
                    await interaction.response.send_message(embed=embed)
                elif option == "Edit":
                    view = Staff_config_edit(interaction.user, guild_config)
                    await interaction.response.send_message(embed=embed, view=view)
                    view.message = await interaction.original_response()
            
            case "payout":
                embed = discord.Embed(title="Payout Config", description="", color=0x2b2d31)
                data = await self.bot.payout_config.find(interaction.guild.id)
                if data is None:
                    data = {
                        '_id': interaction.guild.id,
                        'queue_channel': None,
                        'pending_channel': None,
                        'payout_channel': None,
                        'manager_roles': [],
                        'event_manager_roles': [],
                        'log_channel': None,
                        'default_claim_time': 3600,
                        'express': False,
                    }
                    await self.bot.payout_config.insert(data)
                
                embed.description += f"**Queue Channel:** {interaction.guild.get_channel(data['queue_channel']).mention if data['queue_channel'] else '`Not Set`'}\n"
                embed.description += f"**Pending Channel:** {interaction.guild.get_channel(data['pending_channel']).mention if data['pending_channel'] else '`Not Set`'}\n"
                embed.description += f"**Log Channel:** {interaction.guild.get_channel(data['log_channel']).mention if data['log_channel'] else '`Not Set`'}\n"
                embed.description += f"**Payout Channel:** {interaction.guild.get_channel(data['payout_channel']).mention if data['payout_channel'] else '`Not Set`'}\n"
                embed.description += f"**Manager Roles:** {', '.join([f'<@&{role}>' for role in data['manager_roles']]) if data['manager_roles'] else '`Not Set`'}\n"
                embed.description += f"**Event Manager Roles:** {', '.join([f'<@&{role}>' for role in data['event_manager_roles']]) if data['event_manager_roles'] else '`Not Set`'}\n"
                embed.description += f"**Default Claim Time:** {humanfriendly.format_timespan(data['default_claim_time'])}\n"
            
                if option == "Show":
                    await interaction.response.send_message(embed=embed)
                elif option == "Edit":
                    view = Payout_Config_Edit(data, interaction.user)
                    await interaction.response.send_message(embed=embed, view=view)
                    view.message = await interaction.original_response()
            
            case "tickets":                
                ticket_config = await self.bot.tickets.config.find(interaction.guild.id)
                if ticket_config is None:
                    ticket_config = {'_id': interaction.guild.id,'category': None,'channel': None,'logging': None,'panels': {},'last_panel_message_id': None, 'transcript': None}
                    await self.bot.tickets.config.insert(ticket_config)
        
                embed = discord.Embed(title="Ticket Config", color=0x2b2d31, description="")
                embed.description += f"**Category:**" + (f" <#{ticket_config['category']}>" if ticket_config['category'] is not None else "`None`") + "\n"
                embed.description += f"**Channel:**" + (f" <#{ticket_config['channel']}>" if ticket_config['channel'] is not None else "`None`") + "\n"
                embed.description += f"**Logging:**" + (f" <#{ticket_config['logging']}>" if ticket_config['logging'] is not None else "`None`") + "\n"
                embed.description += f"**Transcript:**" + (f" <#{ticket_config['transcript']}>" if ticket_config['transcript'] is not None else "`None`") + "\n"
                embed.description += f"**Panel Message:**" + (f" {ticket_config['last_panel_message_id']}" if ticket_config['last_panel_message_id'] is not None else "`None`") + "\n"
                embed.description += f"**Panels:**" + (f"`{len(ticket_config['panels'])}`" if ticket_config['panels'] is not None else "`0`") + "\n"
        
                if option == "Show":
                    await interaction.response.send_message(embed=embed)
                elif option == "Edit":
                    view = Ticket_Config_Edit(interaction.user, ticket_config)
                    await interaction.response.send_message(embed=embed, view=view)
                    view.message = await interaction.original_response()
                    await view.wait()
                    if view.value:
                        await self.bot.tickets.config.update(view.data)

            case "leveling":
                leveling_config = await self.bot.level.get_config(interaction.guild)
                embed = discord.Embed(title="Leveling Config", color=interaction.client.default_color, description="")
                embed.description += f"**Leveling:** {leveling_config['enabled']}\n"
                embed.description += f"**Clear On Leave:** {leveling_config['clear_on_leave']}\n"
                embed.description += f"**Announcement Channel:** {interaction.guild.get_channel(leveling_config['announcement_channel']).mention if leveling_config['announcement_channel'] else '`None`'}\n"
                embed.description += f"**Global Multiplier:** `{leveling_config['global_multiplier']}`\n"
                embed.description += f"**Global Cooldown:** `{humanfriendly.format_timespan(leveling_config['cooldown'])}`\n"
                embed.description += f"**Multiplier Roles:**\n"
                for role, multi in leveling_config['multipliers']['roles'].items():
                    embed.description += f"> `{multi}`: <:tgk_blank:1072224743266193459> <@&{role}> \n"
                
                embed.description += f"**Multiplier Channels:**\n"
                for channel, multi in leveling_config['multipliers']['channels'].items():
                    embed.description += f"> `{multi}`: <:tgk_blank:1072224743266193459> <#{channel}> \n"
                
                rewards_roles = leveling_config['rewards']
                rewards_roles = sorted(rewards_roles.items(), key=lambda x: int(x[0]))
                embed.description += f"**Rewards:**\n"
                for level, role in rewards_roles:
                    embed.description += f"> `{level}` : <:tgk_blank:1072224743266193459> <:tgk_blank:1072224743266193459> <@&{role}>\n"

                embed.description += f"**Blacklist:**\n> Roles: {','.join([f'<@&{role}>' for role in leveling_config['blacklist']['roles']]) if leveling_config['blacklist']['roles'] else '`None`'}\n> Channels: {','.join([f'<#{channel}>' for channel in leveling_config['blacklist']['channels']]) if leveling_config['blacklist']['channels'] else '`None`'}\n"

                if option == "Show":
                    await interaction.response.send_message(embed=embed)
                elif option == "Edit":
                    view = LevelingConfig(interaction.user, leveling_config)
                    await interaction.response.send_message(embed=embed, view=view)
                    view.message = await interaction.original_response()
                    
            case "perks":
                perk_config = await self.bot.Perk.get_data("config", interaction.guild.id, interaction.user.id)
                if not perk_config:
                    perk_config = await self.bot.Perk.create("config", interaction.user.id, interaction.guild.id)
                embed = await self.bot.Perk.get_config_embed(interaction.guild)

                view = PerkConfig(interaction.user, perk_config)
                await interaction.response.send_message(embed=embed, view=view)
                view.message = await interaction.original_response()
            
            case "auctions":
                
                auction_data = await self.bot.auction.get_config(interaction.guild.id)

                embed = discord.Embed(title=f"{interaction.guild.name} Auction Config", color=self.bot.default_color, description="")
                embed.description += f"**Category:** <#{auction_data['category']}> \n" if auction_data['category'] else "**Category:** `None`\n"
                embed.description += f"**Request Channel:** <#{auction_data['request_channel']}> \n" if auction_data['request_channel'] else "**Request Channel:** `None`\n"
                embed.description += f"**Queue Channel:** <#{auction_data['queue_channel']}> \n" if auction_data['queue_channel'] else "**Queue Channel:** `None`\n"
                embed.description += f"**Bid Channel:** <#{auction_data['bid_channel']}> \n" if auction_data['bid_channel'] else "**Bid Channel:** `None`\n"
                embed.description += f"**Payment Channel:** <#{auction_data['payment_channel']}> \n" if auction_data['payment_channel'] else "**Payment Channel:** `None`\n"
                embed.description += f"**Manager Roles:** {', '.join([f'<@&{role}>' for role in auction_data['manager_roles']]) if len(auction_data['manager_roles']) > 0 else '`None`'}\n"
                embed.description += f"**Ping Role:** {interaction.guild.get_role(auction_data['ping_role']).mention if auction_data['ping_role'] else '`None`'}\n"
                embed.description += f"**Minimum Worth:** {auction_data['minimum_worth']:,}\n" if auction_data['minimum_worth'] else '**Minimum Worth:** `None`'
                if option == "Show":
                    await interaction.response.send_message(embed=embed)
                if option == "Edit":
                    view = AuctionConfig(interaction.user, auction_data)
                    await interaction.response.send_message(embed=embed, view=view)
                    view.message = await interaction.original_response()
            
            case "giveaways":
                giveaway_data = await self.bot.giveaway.get_config(interaction.guild)
                embed = discord.Embed(title=f"{interaction.guild.name} Giveaway Config", color=self.bot.default_color, description="")
                embed.description += f"**Manager Roles:** {', '.join([f'<@&{role}>' for role in giveaway_data['manager_roles']]) if len(giveaway_data['manager_roles']) > 0 else '`None`'}\n"
                embed.description += f"**Logging Channel:** {interaction.guild.get_channel(giveaway_data['log_channel']).mention if giveaway_data['log_channel'] else '`None`'}\n"
                embed.description += f"**Dm Message:** ```\n{giveaway_data['dm_message']}\n```\n"
                embed.description += f"**Blacklist:**\n {', '.join([f'<@&{(role)}>' for role in giveaway_data['blacklist']]) if len(giveaway_data['blacklist']) > 0 else '`None`'}\n"
                embed.description += f"**Global Bypass:**\n {', '.join([f'<@&{(role)}>' for role in giveaway_data['global_bypass']]) if len(giveaway_data['global_bypass']) > 0 else '`None`'}\n"
                mults = giveaway_data['multipliers']
                mults = sorted(mults.items(), key=lambda x: int(x[1]))
                embed.description += f"\n**Multipliers:**\n"
                for value, multi in mults:
                    embed.description += f"> `{multi}` : <@&{value}>\n"

                if option == "Show":
                    await interaction.response.send_message(embed=embed)
                if option == "Edit":
                    view = GiveawayConfig(giveaway_data, interaction.user)
                    await interaction.response.send_message(embed=embed, view=view)
                    view.message = await interaction.original_response()

            case "blacklist":
                await interaction.response.defer()
                blacklist_data = await self.bot.blacklist.get_config(interaction.guild_id)
                embed = discord.Embed(title=f"{interaction.guild.name} Blacklist Config", color=self.bot.default_color, description="")
                embed.description += f"**Mod Roles:** {', '.join([f'<@&{role}>' for role in blacklist_data['mod_roles']]) if len(blacklist_data['mod_roles']) > 0 else '`None`'}\n"
                embed.description += f"**Logging Channel:** {interaction.guild.get_channel(blacklist_data['log_channel']).mention if blacklist_data['log_channel'] else '`None`'}\n"
                embed.description += f"**Profiles:** {', '.join([f'`{position.capitalize()}`' for position in blacklist_data['profiles'].keys()]) if len(blacklist_data['profiles'].keys()) > 0 else '`None`'}\n"
                if option == "Show":
                    await interaction.followup.send(embed=embed)
                    return
                view = Blacklist_Config(interaction.user, blacklist_data)                
                await interaction.followup.send(embed=embed, view=view)
                view.message = await interaction.original_response()
            
            case "events":
                data = await self.bot.events.get_config(interaction.guild.id)
                embed = discord.Embed(title="Event Request System", color=interaction.client.default_color, description="")
                embed.description += f"**Manager Roles:** {', '.join([f'<@&{role}>' for role in data['manager_roles']]) if len(data['manager_roles']) > 0 else '`None`'}\n"
                embed.description += f"**Request Channel:** {interaction.guild.get_channel(data['request_channel']).mention if data['request_channel'] else '`None`'}\n"
                embed.description += f"**Request Queue:** {interaction.guild.get_channel(data['request_queue']).mention if data['request_queue'] else '`None`'}\n"
                embed.description += f"**Events:** {', '.join([f'`{event}`' for event in data['events'].keys()]) if len(data['events'].keys()) > 0 else '`None`'}\n"

                if option == "Show":
                    await interaction.response.send_message(embed=embed)
                if option == "Edit":
                    view = request_system.Config(interaction.user, data)
                    await interaction.response.send_message(embed=embed, view=view)
                    view.message = await interaction.original_response()

            case _:
                await interaction.response.send_message("This command is not available for this server", ephemeral=True)


class JoinGateBackEnd(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.joingate_cache = {}

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in await self.bot.ss.join_gate.get_all():self.bot.joingate_cache[guild["_id"]] = guild
    
    @staticmethod
    def is_cancerous(text: str) -> bool:
        if text is None: return False
        for segment in text.split():
            for char in segment:
                if not (char.isascii() and char.isalnum()):
                    return True
        return False

    @staticmethod
    def strip_accs(text):
        try:
            text = unicodedata.normalize("NFKC", text)
            text = unicodedata.normalize("NFD", text)
            text = unidecode.unidecode(text)
            text = text.encode("ascii", "ignore")
            text = text.decode("utf-8")
        except Exception as e:
            pass
        return str(text)

    async def nick_maker(self, guild: discord.Guild, old_shit_nick):
        old_shit_nick = self.strip_accs(old_shit_nick)
        new_cool_nick = re.sub("[^a-zA-Z0-9 \n.]", "", old_shit_nick)
        new_cool_nick = " ".join(new_cool_nick.split())
        new_cool_nick = stringcase.lowercase(new_cool_nick)
        new_cool_nick = stringcase.titlecase(new_cool_nick)
        default_name = "Request a new name"
        if len(new_cool_nick.replace(" ", "")) <= 1 or len(new_cool_nick) > 32:
            new_cool_nick = default_name
        else:
            pass
        return new_cool_nick

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot: return
        if member.guild.id not in self.bot.joingate_cache.keys(): return
        data = self.bot.joingate_cache[member.guild.id]
        if not data["joingate"]["enabled"]: return
        if member.id in data["joingate"]["whitelist"]: return

        fail = self.bot.dispatch("joingate_check", member)
        if fail: return

        if data["joingate"]["decancer"]:
            if member.name.startswith("カ"): return
            is_cancerous = self.is_cancerous(member.global_name)
            if not is_cancerous:
                if not member.display_name: return
                is_cancerous = self.is_cancerous(member.display_name)
            if is_cancerous:
                new_nick = await self.nick_maker(member.guild, member.display_name)
                
                embed = discord.Embed(color=discord.Color.green(), title="Decancer", description="")
                embed.description += f"**Offender:** {member.mention}\n"
                embed.description += f"**Action:** Nickname Decancer\n"
                embed.description += f"**Reason:** Nickname contained non-ascii characters\n"
                embed.description += f"**Moderator:** {self.bot.user.mention}\n"
                embed.set_footer(text=f"User ID: {member.id}")
                embed.timestamp = datetime.datetime.utcnow()

                #logchannel = member.guild.get_channel(data["joingate"]["logchannel"])
                try:
                    await member.edit(nick=new_nick, reason="joingate decancer")
                except:
                    return
                #if logchannel: await logchannel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_joingate_check(self, member: discord.Member):
        data = self.bot.joingate_cache[member.guild.id]
        guild = member.guild
        if not data['joingate']['accountage']: return
        if (discord.utils.utcnow() - member.created_at).days < int(data['joingate']['accountage']):
            try:
                await member.send(f"Your account is too new to join this server. Please wait {data['joingate']['accountage']} days before joining.")
            except discord.Forbidden:
                pass
            if data["joingate"]["action"] == "kick":
                await member.kick(reason="joingate kick")
            elif data["joingate"]["action"] == "ban":
                await member.ban(reason="joingate ban")
            embed = discord.Embed(title="Kick", description="")
            embed.description += f"**Target:** {member.mention}\n"
            embed.description += f"**Action:** {data['joingate']['action'].title()}\n"
            embed.description += f"**Reason:** Account age is less than joingate account age\n"
            embed.description += f"**Moderator:** {self.bot.user.mention}\n"
            embed.set_footer(text=f"ID: {member.id}")
            embed.timestamp = discord.utils.utcnow()
            embed.color = discord.Color.red()

            logchannel = member.guild.get_channel(data["joingate"]["logchannel"])
            if logchannel: await logchannel.send(embed=embed)
            return True
        else:
            roles = [guild.get_role(role) for role in data["joingate"]["autorole"]]
            await member.edit(roles=roles, reason="joingate autorole")

async def setup(bot):
    await bot.add_cog(serversettings(bot))
    await bot.add_cog(JoinGateBackEnd(bot))
