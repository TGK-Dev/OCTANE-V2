import discord
import pytz
from discord import Interaction, app_commands
import datetime
from typing import TypedDict
from discord.ext import commands, tasks
from utils.db import Document



class UserActivity(TypedDict):
    _id: int
    messages: int
    last_message: int

@app_commands.default_permissions(administrator=True)
class ActivityLeaderboard(commands.GroupCog, name="activity"):
    def __init__(self, bot):
        self.bot = bot
        self.config_cach = {}
        self.db = self.bot.mongo['Activity']
        self.config = Document(self.db, 'config')
        self.messages = Document(self.db, 'messages')
        self.update_leaderboard.start()
        self.ready = False

    @tasks.loop(minutes=5)
    async def update_leaderboard(self):
        config = await self.config.find(785839283847954433)
        if not config: return
        lb_channel = self.bot.get_channel(config['lb_channel'])
        if not lb_channel: return

        users = await self.messages.get_all()
        users = sorted(users, key=lambda x: x['messages'], reverse=True)
        embed = discord.Embed(title="Message Leaderboard", color=self.bot.default_color, 
                              description="",timestamp=datetime.datetime.now().astimezone(pytz.timezone('Asia/Kolkata')))
        for index, user in enumerate(users[:10]):
            member = lb_channel.guild.get_member(user['_id'])
            if not member: continue
            embed.description += f"{index + 1}. {member.mention} - {user['messages']} messages\n"
        embed.set_footer(text="Last updated at")
        await lb_channel.purge(limit=10)
        await lb_channel.send(embed=embed)

    @update_leaderboard.before_loop
    async def before_update_leaderboard(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_ready(self):
        self.config_cach = await self.config.find(785839283847954433)
        self.ready = True

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if self.ready != True: return
        if message.author.bot: return
        if not message.guild: return

        if self.config_cach == {}: return
        if message.channel.id != self.config_cach['channel']: return

        user_data = await self.messages.find(message.author.id)
        if not user_data:
            user_data = {"_id": message.author.id, "messages": 1, "last_message": datetime.datetime.utcnow()}
            await self.messages.insert(user_data)
            return
        
        if user_data['last_message'] + datetime.timedelta(seconds=10) > datetime.datetime.utcnow():
            return
        user_data['messages'] += 1
        user_data['last_message'] = datetime.datetime.utcnow()
        await self.messages.update(user_data)

    @app_commands.command(name="set-channel", description="Set the channel for the message tracking leaderboard")
    async def set_channel(self, interaction: Interaction, channel: discord.TextChannel):
        config = await self.config.find(interaction.guild.id)
        if not config:
            config = {"_id": interaction.guild.id, "channel": channel.id}
            await self.config.insert(config)
        
        config['channel'] = channel.id
        await self.config.update(config)
        self.config_cach = config
        await interaction.response.send_message(f"Set the channel to {channel.mention}", ephemeral=True)

    @app_commands.command(name="set-lb", description="Set the leaderboard channel")
    async def set_lb(self, interaction: Interaction, channel: discord.TextChannel):
        config = await self.config.find(interaction.guild.id)
        if not config:
            await interaction.response.send_message("You need to set the message tracking channel first", ephemeral=True)
            return
        
        config['lb_channel'] = channel.id
        await self.config.update(config)
        self.config_cach = config
        await interaction.response.send_message(f"Set the leaderboard channel to {channel.mention}", ephemeral=True)
    
    @app_commands.command(name="reset", description="Reset the message count for a user")
    async def reset(self, interaction: Interaction, member: discord.Member):
        user_data = await self.messages.find(member.id)
        if not user_data:
            await interaction.response.send_message("This user has no messages", ephemeral=True)
            return
        user_data['messages'] = 0
        await self.messages.update(user_data)
        await interaction.response.send_message(f"Reset the message count for {member.mention}", ephemeral=True)

    @app_commands.command(name="reset-lb", description="Reset the leaderboard")
    async def reset_lb(self, interaction: Interaction):
        users = await self.messages.get_all()
        await interaction.response.send_message("Resetting the leaderboard", ephemeral=True)
        data = []
        for user in users:
            user['messages'] = 0
            data.append(user)
        await self.messages.bulk_update(data)
        await interaction.edit_original_response(content="Leaderboard reset successfully!")


async def setup(bot):
    await bot.add_cog(ActivityLeaderboard(bot), guilds=[discord.Object(785839283847954433)])          
