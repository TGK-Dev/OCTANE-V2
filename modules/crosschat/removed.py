import discord
import datetime
from discord.ext import commands, tasks
from discord import app_commands, Interaction
from utils.db import Document

class Crosschat(commands.GroupCog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Document(bot.db, "crosschat")
        self.config = {}
        self.message_cache = {}
        self.clean_up = self.clear_cache.start()
    
    def cog_unload(self):
        self.clean_up.cancel()
    
    async def create_config(self):
        data = {
            "_id": "master",
            "tgk_channel": None,
            "tgk_webhook": None,
            "valley_channel": None,
            "valley_webhook": None,
            "active": False,
            "blocked": []
        }
        await self.db.insert(data)
        return data

    @tasks.loop(hours=2)
    async def clear_cache(self):
        cache = self.message_cache.copy()
        for message_id, data in cache:
            if (datetime.datetime.utcnow() - data['added_at']).total_seconds() > 86400:
                del self.message_cache[message_id]

    @clear_cache.before_loop
    async def before_clear_cache(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_ready(self):
        data = await self.db.find({"_id": "master"})
        if not data:
            data = await self.create_config()
        self.config = data
        self.config['tgk_hook'] = await self.bot.fetch_webhook(data['tgk_webhook'])
        self.config['valley_hook'] = await self.bot.fetch_webhook(data['valley_webhook'])

    @app_commands.command(name="set-channel", description="Set the channel for crosschat")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_channel(self, interaction: Interaction, channel: discord.TextChannel):
        data = await self.db.find({"_id": "master"})
        await interaction.response.send_message("Setting the channel for crosschat")
        if not data:
            data = await self.create_config()
        if interaction.guild.id == 785839283847954433:
            data["tgk_channel"] = channel.id
            webhook = await channel.create_webhook(name="TGK Side Hook")
            data["tgk_webhook"] = webhook.id
        elif interaction.guild.id == 1072079211419938856:
            data["valley_channel"] = channel.id
            webhook = await channel.create_webhook(name="Valley Side Hook")
            data["valley_webhook"] = webhook.id
        await self.db.update(data)
        await interaction.edit_original_response(content=None, embed=discord.Embed(description="Successfully set the channel for crosschat", color=self.bot.default_color))
        self.config = data
        self.config['tgk_hook'] = await self.bot.fetch_webhook(data['tgk_webhook'])
        self.config['valley_hook'] = await self.bot.fetch_webhook(data['valley_webhook'])
    
    @app_commands.command(name="toggle", description="Toggle crosschat")
    @app_commands.checks.has_permissions(administrator=True)
    async def toggle(self, interaction: Interaction):
        data = await self.db.find({"_id": "master"})
        await interaction.response.send_message("Toggling crosschat", ephemeral=True)
        if not data:
            data = await self.create_config()
        if data['active']:
            data['active'] = False
        else:
            data['active'] = True
        await self.db.update(data)
        
        self.config['active'] = data['active']
        await interaction.edit_original_response(content=None, embed=discord.Embed(description=f"Successfully toggled to {data['active']}", color=self.bot.default_color))

        tgk_channel = self.bot.get_channel(self.config['tgk_channel'])
        valley_channel = self.bot.get_channel(self.config['valley_channel'])
        embed = discord.Embed(description=f"Crosschat is now {'active' if data['active'] else 'inactive'}", color=self.bot.default_color)
        await tgk_channel.send(embed=embed)
        await valley_channel.send(embed=embed)


    @app_commands.command(name="block", description="Block a user from crosschat")
    @app_commands.checks.has_permissions(administrator=True)
    async def block(self, interaction: Interaction, user: discord.User):
        data = await self.db.find({"_id": "master"})
        await interaction.response.send_message("Blocking user from crosschat")
        if not data:
            data = await self.create_config()
        if user.id in data['blocked']:
            await interaction.edit_original_response(content=None, embed=discord.Embed(description="User is already blocked", color=self.bot.default_color))
            return
        data['blocked'].append(user.id)
        await self.db.update(data)
        self.config['blocked'] = data['blocked']
        await interaction.edit_original_response(content=None, embed=discord.Embed(description="Successfully blocked user from crosschat", color=self.bot.default_color))
    
    @app_commands.command(name="unblock", description="Unblock a user from crosschat")
    @app_commands.checks.has_permissions(administrator=True)
    async def unblock(self, interaction: Interaction, user: discord.User):
        data = await self.db.find({"_id": "master"})
        await interaction.response.send_message("Unblocking user from crosschat")
        if not data:
            data = await self.create_config()
        if user.id not in data['blocked']:
            await interaction.edit_original_response(content=None, embed=discord.Embed(description="User is not blocked", color=self.bot.default_color))
            return
        data['blocked'].remove(user.id)
        await self.db.update(data)
        self.config['blocked'] = data['blocked']
        await interaction.edit_original_response(content=None, embed=discord.Embed(description="Successfully unblocked user from crosschat", color=self.bot.default_color))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot: return
        if not message.guild: return
        if message.guild.id not in [785839283847954433, 1072079211419938856]: return
        if self.config == {}:
            config = await self.db.find({"_id": "master"})
            self.config = config

        if self.config['active'] == False: return
        if message.channel.id not in [self.config['tgk_channel'], self.config['valley_channel']]: return

        if message.author.id in self.config['blocked']: 
            await message.add_reaction("<:tgk_deactivated:1082676877468119110>")
            return
        kwargs = {
            "content": message.content,
            "username": message.author.display_name,
            "avatar_url": message.author.avatar.url if message.author.avatar else message.author.default_avatar.url,
            "allowed_mentions": discord.AllowedMentions.none(),
            "embeds": [],
            "wait": True
        }
        if len(message.attachments):
            for attachment in message.attachments:
                if attachment.url.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                    kwargs["embeds"].append(discord.Embed(color=self.bot.default_color).set_image(url=attachment.url))
                    break
        
        if message.reference:

            try:
                reply_message = await message.channel.fetch_message(message.reference.message_id)
                embed = discord.Embed(description="", color=self.bot.default_color)
                embed.set_author(name=reply_message.author.display_name, icon_url=reply_message.author.avatar.url if reply_message.author.avatar else reply_message.author.default_avatar.url)
                embed.description = reply_message.content
                if len(reply_message.attachments) > 0:
                    for attachment in reply_message.attachments:
                        if attachment.url.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                            embed.set_image(url=attachment.url)
                            break
                kwargs["embeds"].append(embed)
                if reply_message.webhook_id:
                    for msg_embed in reply_message.embeds:
                        kwargs["embeds"].append(msg_embed)

            except discord.NotFound:
                pass
            
        if message.guild.id == 785839283847954433:
            webhook = self.config['valley_hook']
        elif message.guild.id == 1072079211419938856:
            webhook = self.config['tgk_hook']
        if len(kwargs['embeds']) > 10:
            kwargs['embeds'] = kwargs['embeds'][:10]
        if kwargs['content'] is None and len(kwargs['embeds']) == 0 and len(message.attachments) == 0:
            await message.add_reaction("<:tgk_deactivated:1082676877468119110>")
            return
        clone_message = await webhook.send(**kwargs)

        self.message_cache[message.id] = {
            "message": clone_message.id,
            "channel": clone_message.channel.id,
            "added_at": datetime.datetime.utcnow()
        }
    
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if after.id not in self.message_cache.keys():
            return
        kwargs = {
            "content": after.content,
        }
        if after.guild.id == 785839283847954433:
            webhook = self.config['valley_hook']
        elif after.guild.id == 1072079211419938856:
            webhook = self.config['tgk_hook']
        await webhook.edit_message(self.message_cache[after.id]['message'], **kwargs)


    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.id not in self.message_cache.keys():
            return
        if message.guild.id == 785839283847954433:
            webhook = self.config['valley_hook']
        elif message.guild.id == 1072079211419938856:
            webhook = self.config['tgk_hook']
        await webhook.delete_message(self.message_cache[message.id]['message'])

async def setup(bot):
    await bot.add_cog(Crosschat(bot), guilds=[discord.Object(785839283847954433), discord.Object(1072079211419938856)])

async def teardown(bot):
    await bot.remove_cog("Crosschat")