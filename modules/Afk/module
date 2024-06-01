import discord
from discord.ext import commands
from discord import app_commands, Interaction
import datetime
from utils.db import Document

class Afk(commands.GroupCog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.afk = Document(bot.db, "afk")
        self.bot.current_afk = {}

    @commands.Cog.listener()
    async def on_ready(self):
        current_afks = await self.bot.afk.get_all()
        for afk in current_afks:
            if afk['afk'] == True:
                self.bot.current_afk[afk["_id"]] = afk
    
    @commands.Cog.listener()
    async def on_afk_ping(self, message:discord.Message, user:discord.Member):
        user_data = await self.bot.afk.find(user.id)
        user_data['pings'].append({
            "id":message.author.id,
            "message": message.content if len(message.content) <= 100 else f"{message.content[:100]}...",
            "jump_url": message.jump_url,
            "pinged_at": f'<t:{int(datetime.datetime.timestamp(datetime.datetime.now()))}:R>',
            "timestamp": datetime.datetime.now(),
            "channel_id": message.channel.id,
            "guild_id": message.guild.id
        })
        if len(user_data['pings']) > 10:
            while len(user_data['pings']) > 10:
                user_data['pings'].pop(0)
        await self.bot.afk.update(user_data)
        try:
            await message.reply(f"`{user_data['last_nick']}` is afk: {user_data['reason']}", delete_after=10, allowed_mentions=discord.AllowedMentions.none(), mention_author=False)
        except discord.HTTPException:
            await message.channel.send(f"{message.author.mention} `{user_data['last_nick']}` is afk: {user_data['reason']}", delete_after=10, allowed_mentions=discord.AllowedMentions.none())                                       

    @commands.Cog.listener()
    async def on_afk_return(self, message):
        user_data = await self.bot.afk.find(message.author.id)
        
        if user_data is None:
            if '[AFK]' in message.author.display_name:
                try:
                    await message.author.edit(nick=message.author.display_name.replace('[AFK]', ''))
                except discord.Forbidden:
                    pass
            if message.author.id in self.bot.current_afk.keys():
                self.bot.current_afk.pop(message.author.id)
            return
        
        if len(user_data['pings']) != 0:
            embeds = []
            for index,user_data in enumerate(user_data['pings']):
                guild = self.bot.get_guild(user_data['guild_id'])
                user: discord.Member = guild.get_member(user_data['id'])
                if not user:
                    user = await self.bot.fetch_user(user_data['id'])
                pinged_at = user_data['pinged_at']
                jump_url = user_data['jump_url']
                content = user_data['message']
                channel = guild.get_channel(user_data['channel_id'])
                channel_name = channel.name if channel else "Unknown Channel"
                embed = discord.Embed(color=0x2b2d31 , timestamp=user_data['timestamp'])
                embed.set_author(name = f'{user.global_name if user.global_name != None else user.display_name}', icon_url = user.avatar.url if user.avatar else user.default_avatar)
                embed.description = f"<a:tgk_redSparkle:1072168821797965926> [`You were pinged in #{channel_name}.`]({jump_url}) {pinged_at}\n"
                embed.description += f"<a:tgk_redSparkle:1072168821797965926> **Message:** {content}"
                embed.set_footer(text = f"Pings you received while you were AFK • Pinged at")
                embeds.append(embed)
            try:
                await message.author.send(embeds=embeds)
            except:
                await message.reply("I couldn't send you the pings you received while you were AFK because you have DMs disabled.", delete_after=10, mention_author=False)
        try:
            user_data = await self.bot.afk.find(message.author.id)
            user_data['afk'] = False
            user_data['reason'] = None
            user_data['afk_at'] = None
            user_data['last_nick'] = None
            user_data['pings'] = []
            await self.bot.afk.update(user_data)
            self.bot.current_afk.pop(message.author.id)
        except KeyError:
            pass
        
        try:
            if "last_nick" in user_data.keys():
                await message.author.edit(nick=user_data['last_nick'])
            else:
                await message.author.edit(nick=message.author.display_name.replace('[AFK]', ''))
        except discord.Forbidden:
            pass
            
        await message.reply(f"Welcome back {message.author.mention}!", delete_after=10)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.guild is None or message.content is None: 
            return
        if message.guild:
            if message.guild.id != 785839283847954433:
                return
        if message.author.id in self.bot.current_afk.keys():
            data = self.bot.current_afk[message.author.id]
            if message.channel.id in data['ignore_channels']:
                return
            self.bot.dispatch("afk_return", message)
        if len(message.mentions) > 0:
            for user in message.mentions:
                if user.id in self.bot.current_afk.keys() and user in message.channel.members:
                    data = self.bot.current_afk[user.id]
                    if message.channel.id in data['ignore_channels']:   
                        return
                    return self.bot.dispatch("afk_ping", message, user)
        if message.reference is not None:
            try:
                reference_message = await message.channel.fetch_message(message.reference.message_id)
            except:
                return
            if reference_message.author.id in self.bot.current_afk.keys():
                data = self.bot.current_afk[reference_message.author.id]
                if message.channel.id in data['ignore_channels']:
                    return
                
                self.bot.dispatch("afk_ping", message, reference_message.author)
    
    @app_commands.command(name="set", description="Set your afk status")
    @app_commands.describe(reason="The reason for being afk")
    async def _set(self, interaction: Interaction, reason: str=None):
        if reason:
            if len(reason.split(" ")) > 30:
                await interaction.response.send_message("Your afk reason must be less than 30 words.", ephemeral=True)
            
        user_data = await self.bot.afk.find(interaction.user.id)
        if not user_data:
            user_data = {
                '_id': interaction.user.id,
                'guild_id': interaction.guild.id,
                'reason': reason,
                'last_nick': interaction.user.display_name,
                'pings': [],
                'afk_at': datetime.datetime.now(),
                'ignore_channels': [],
                'afk': None
            }
            await self.bot.afk.insert(user_data)

        user_data['afk'] = True
        user_data['reason'] = reason
        user_data['afk_at'] = datetime.datetime.now()
        user_data['last_nick'] = interaction.user.display_name
        await self.bot.afk.update(user_data)
        self.bot.current_afk[interaction.user.id] = user_data

        await interaction.response.send_message(f"`{interaction.user.display_name}` I set your status to {reason if reason else 'afk'}", ephemeral=True)
    
    @app_commands.command(name="remove", description="Remove a member from afk")
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.describe(member="The member to remove from afk")
    async def _remove(self, interaction: Interaction, member: discord.Member):

        user_data = await self.bot.afk.find(member.id)
        if not user_data:
            await interaction.response.send_message(f"`{member.display_name}` is not afk.", ephemeral=True)
            return
        await self.bot.afk.delete_by_id(member.id)

        await interaction.response.send_message(f"`{member.display_name}` is no longer afk.", ephemeral=True)
    
    @app_commands.command(name="ignore", description="Ignore a channel while afk")
    @app_commands.describe(channel="The channel to ignore")
    async def _ignore(self, interaction: Interaction, channel: discord.TextChannel):
        user_data = await self.bot.afk.find(interaction.user.id)
        if not user_data:
            user_data = {
                '_id': interaction.user.id,
                'guild_id': interaction.guild.id,
                'reason': None,
                'last_nick': interaction.user.display_name,
                'pings': [],
                'afk_at': datetime.datetime.now(),
                'ignore_channels': [],
                'afk': None
            }
            await self.bot.afk.insert(user_data)
        if channel.id in user_data['ignore_channels']:
            user_data['ignore_channels'].remove(channel.id)
            await interaction.response.send_message(f"I will no longer ignore {channel.mention} while you are afk.", ephemeral=True)
        else:
            user_data['ignore_channels'].append(channel.id)
            await interaction.response.send_message(f"I will now ignore {channel.mention} while you are afk.", ephemeral=True)

        await self.bot.afk.update(user_data)
        if user_data['afk'] == True:
            cache = self.bot.current_afk[interaction.user.id]
            cache['ignore_channels'] = user_data['ignore_channels']
            self.bot.current_afk[interaction.user.id] = cache

async def setup(bot):
    await bot.add_cog(Afk(bot), guilds=[discord.Object(785839283847954433)])