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
from utils.views.perks_system import PerkConfig
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
        app_commands.Choice(name="Join Verification", value="join_gate"),
        app_commands.Choice(name="Staff Managment", value="staff"),
        app_commands.Choice(name="Perks System", value="perks"),
        app_commands.Choice(name="Payout System", value="payout"),
        app_commands.Choice(name="Tickets System", value="tickets"),
        app_commands.Choice(name="Leveling System", value="leveling"),
    ]
    
    @app_commands.command(name="serversettings", description="Change the settings of the server")
    @app_commands.choices(settings=settings)
    @app_commands.describe(option="Show or edit the settings", settings="The settings you want to change")
    @app_commands.default_permissions(administrator=True)
    async def serversettings(self, interaction: discord.Interaction, settings: app_commands.Choice[str], option: Literal['Show', 'Edit']):
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
                guild_config = await self.bot.staff_db.get_config(interaction.guild)
                if interaction.user.id != interaction.guild.owner.id and interaction.user.id not in guild_config['owners']:
                    return await interaction.response.send_message("You are not allowed to use this command!", ephemeral=True)
                
                embed = discord.Embed(title=f"{interaction.guild.name}'s Staff Settings", description="")
                embed.description += f"**Owners:** {', '.join([f'<@{owner}>' for owner in guild_config['owners']])}\n"
                embed.description += f"**Staff Managers:** {', '.join([f'<@{role}>' for role in guild_config['staff_manager']])}\n"
                embed.description += f"**Base Role:**" + (f" <@&{guild_config['base_role']}>" if guild_config['base_role'] != None else "`None`") + "\n"
                embed.description += f"**Leave Role:**" + (f" <@&{guild_config['leave_role']}>" if guild_config['leave_role'] != None else "`None`") + "\n"        
                embed.description += f"**Leave Channel:**" + (f" <#{guild_config['leave_channel']}>" if guild_config['leave_channel'] != None else "`None`") + "\n"
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
                        'manager_roles': [],
                        'event_manager_roles': [],
                        'log_channel': None,
                        'default_claim_time': 3600,
                    }
                    await self.bot.payout_config.insert(data)
                
                embed.description += f"**Queue Channel:** {interaction.guild.get_channel(data['queue_channel']).mention if data['queue_channel'] else '`Not Set`'}\n"
                embed.description += f"**Pending Channel:** {interaction.guild.get_channel(data['pending_channel']).mention if data['pending_channel'] else '`Not Set`'}\n"
                embed.description += f"**Log Channel:** {interaction.guild.get_channel(data['log_channel']).mention if data['log_channel'] else '`Not Set`'}\n"
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
                level_data = await self.bot.level_config.find(interaction.guild.id)
                if not level_data: 
                    level_data = {"_id": interaction.guild_id,"blacklist": {"channels": [],"roles": [],},'multiplier': {'global': 1, 'channels': {}, 'roles': {}},'cooldown': 8,'clear_on_leave': True}
                    await self.bot.level_config.insert(level_data)
                channel_multipliers = ""
                role_multipliers = ""
                for channel, multiplier in level_data['multiplier']['channels'].items(): channel_multipliers += f"<#{channel}>: `{multiplier}`\n"
                for role, multiplier in level_data['multiplier']['roles'].items(): role_multipliers += f"<@&{role}>: `{multiplier}`\n"
                embed = discord.Embed(title=f"{interaction.guild.name} Leveling Config", color=self.bot.default_color, description="")
                embed.description += f"Global Multiplier: `{level_data['multiplier']['global']}`\n"
                embed.description += f"Cooldown: `{level_data['cooldown'] if level_data['cooldown'] else 'None'}`\n"
                embed.description += f"Clear On Leave: `{'On' if level_data['clear_on_leave'] else 'Off'}`\n"
                embed.description += f"Blacklisted Channels: {', '.join([f'<#{channel}>' for channel in level_data['blacklist']['channels']]) if level_data['blacklist']['channels'] else '`None`'}\n"
                embed.description += f"Blacklisted Roles: {', '.join([f'<@&{role}>' for role in level_data['blacklist']['roles']]) if level_data['blacklist']['roles'] else '`None`'}\n"                
                if option == "Show":
                    await interaction.response.send_message(embed=embed)
                if option == "Edit":
                    view = LevelingConfig(interaction.user, level_data)
                    await interaction.response.send_message(embed=embed, view=view)
                    view.message = await interaction.original_response()
                    
            case "perks":
                perk_data = await self.bot.perk.get_data('config', interaction.guild.id, interaction.user.id)
                if perk_data is None:
                    perk_data = {'_id': interaction.guild.id, 'custom_category': None, 'custom_roles_position': 0}
                    await self.bot.perk.config.insert(perk_data)
                embed = discord.Embed(title=f"{interaction.guild.name} Perk Config", color=self.bot.default_color, description="")
                embed.description += f"Custom Category: {interaction.guild.get_channel(perk_data['custom_category']).mention if perk_data['custom_category'] else '`None`'}\n"
                embed.description += f"Custom Roles Position: `{perk_data['custom_roles_position']}`\n"

                if option == "Show":
                    await interaction.response.send_message(embed=embed)
                if option == "Edit":
                    view = PerkConfig(interaction.user, perk_data)
                    await interaction.response.send_message(embed=embed, view=view)
                    view.message = await interaction.original_response()
            case _:
                await interaction.response.send_message("Invalid option", ephemeral=True)


class JoinGateBackEnd(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.joingate_cache = {}

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in await self.bot.rr.join_gate.get_all():self.bot.joingate_cache[guild["_id"]] = guild["joingate"]
    
    @staticmethod
    def is_cancerous(text: str) -> bool:
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
            if default_name == "Request a new name":
                new_cool_nick = await self.get_random_nick(2)
            elif default_name:
                new_cool_nick = default_name
            else:
                new_cool_nick = "Request a new name"
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
            if self.is_cancerous(member.display_name):
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
