import discord
from discord.ext import commands
from discord import app_commands
from discord.app_commands import Group
from typing import Literal
from utils.db import Document
from utils.views.JoinGateSettings_system import JoinGateSettings_Edit
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
    
    @app_commands.command(name="serversettings", description="Change the settings of the server")
    @app_commands.choices(settings=[app_commands.Choice(name="Join Gate", value="join_gate")])
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
            print(e)
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
            print('doing decancer')
            if self.is_cancerous(member.display_name):
                print('is cancerous')
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
