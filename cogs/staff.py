import discord
import datetime
from discord import app_commands
from discord.ext import commands
from typing import Literal, List
from utils.db import Document
from utils.views import staff_system
from utils.paginator import Paginator
from utils.transformer import TimeConverter
from utils.transformer import MultipleMember
import random
import string

class Staff_DB():
    def __init__(self, bot, Document):
        self.bot = bot
        self.Document = Document
        self.db = bot.mongo['Staff_Database']
        self.config_collection = Document(self.db, "Config")
        self.staff_collection = Document(self.db, "Staff")
    
    async def get_config(self, guild: discord.Guild) -> dict:
        config = await self.config_collection.find(guild.id)
        if config is None: 
            return await self.create_config(guild)
        return config
        
    async def create_config(self, guild: discord.Guild) -> dict:
        data = {'_id': guild.id,'owners': [guild.owner.id],'positions': {},'last_edit': datetime.datetime.utcnow(),'max_positions': 10, 'staff_manager': [], 'leave_role': None, 'base_role': None, 'leave_channel': None}
        await self.config_collection.insert(data)
        return data

    async def get_staff(self, user: discord.User) -> dict:
        staff = await self.staff_collection.find(user.id)
        if staff is None:
            return await self.create_staff(user)
        return staff
    
    async def create_staff(self, user: discord.User) -> dict:
        data = {'_id': user.id, 'positions': {}, 'leave': {'reason': None, 'last_leave': None, 'on_leave': False, 'message_id': None}, 'recovery_code': None}
        await self.staff_collection.insert(data)
        return data
    
class Staff(commands.GroupCog, name="staff", description="Staff management commands"):
    def __init__(self, bot):
        self.bot = bot
        self.bot.staff_db = Staff_DB(bot, Document)
    
    async def staff_position_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:

        guild_config = await self.bot.staff_db.get_config(interaction.guild)
        return [
            app_commands.Choice(name=position.capitalize(), value=position)
            for position in guild_config['positions'].keys()
        ]
    
    leave = app_commands.Group(name="leave", description="set leave for a staff member")

    @app_commands.command(name="appoint", description="Appoint a user to a position")
    @app_commands.describe(user="The user to appoint", position="The position to appoint them to")
    @app_commands.autocomplete(position=staff_position_autocomplete)
    async def appoint(self, interaction: discord.Interaction, user: discord.Member, position: str):
        guild_config = await self.bot.staff_db.get_config(interaction.guild)
        
        if interaction.user.id != interaction.guild.owner.id and interaction.user.id not in guild_config['owners'] and interaction.user.id not in guild_config['staff_manager']:
            return await interaction.response.send_message(f"Only `{interaction.guild.name}'s` owners can use this command", ephemeral=True)

        if position not in guild_config['positions'].keys():
            return await interaction.response.send_message(f"Position `{position.capitalize()}` does not exist", ephemeral=True)
        if user.id in guild_config['positions'][position]:
            return await interaction.response.send_message(f"{user.mention} is already in `{position.capitalize()}`", ephemeral=True)
        
        await interaction.response.send_message(embed=discord.Embed(description="Please wait while we appoint the member...", color=self.bot.default_color))

        post = guild_config['positions'][position]

        if post['owner_only'] == True:
            if interaction.user.id != interaction.guild.owner.id and interaction.user.id not in guild_config['owners']:
                return await interaction.edit_original_response(embed=discord.Embed(description=f"Only `{interaction.guild.name}'s` owners can appoint to `{position.capitalize()}`", color=self.bot.default_color))
        user_data = await self.bot.staff_db.get_staff(user)
        if post['name'] in user_data['positions'].keys():
            return await interaction.edit_original_response(embed=discord.Embed(description=f"{user.mention} is already in `{post['name'].capitalize()}`", color=self.bot.default_color))
        if user_data['recovery_code'] == None:
            key = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            user_data['recovery_code'] = key

            try:
                embed = discord.Embed(title="Recovery Code", description=f"", color=self.bot.default_color)
                embed.description = "You have received a recovery code incase you lost access to your current discord account,"
                embed.description += "If you have lost access to your current discord account, you can use this code to recover your staff account,"
                embed.description += "To recover your account use the command `-recover <code>` in my DMs with account your other account."
                embed.description += "\n\n**Please keep this code safe and do not share it with anyone.**"
                embed.description += "\n**Higer staff members/owners or anyone will never ask you for this code.**"
                embed.add_field(name="Recovery Code", value=key, inline=False)
                await user.send(embed=embed)
                await interaction.followup.send(f"Successfully sent recovery code to {user.mention}", ephemeral=True)
                await self.bot.staff_db.staff_collection.update(user.id, user_data)
            except:
                await interaction.followup.send(f"Failed to send recovery code to {user.mention}, please make sure they have DMs enabled", ephemeral=True)
                user_data['recovery_code'] = None

        post_data = {'name': post['name'], 'appointed_by': interaction.user.id, 'appointed_at': datetime.datetime.utcnow()}
        user_data['positions'][post['name']] = post_data
        post_role = interaction.guild.get_role(post['role'])
        if post_role is None:
            return await interaction.edit_original_response(embed=discord.Embed(description=f"`{post['name'].capitalize()}` role does not exist", color=self.bot.default_color))
        await user.add_roles(post_role, reason=f"Appointed to {post['name'].capitalize()} by {interaction.user}")

        await self.bot.staff_db.staff_collection.update(user.id, user_data)

        await interaction.edit_original_response(embed=discord.Embed(description=f"Successfully appointed {user.mention} to `{post['name'].capitalize()}`", color=self.bot.default_color))
        try:
            await user.send(embed=discord.Embed(description=f"You have been appointed to `{post['name'].capitalize()}` by `{interaction.user}`", color=self.bot.default_color))
        except:
            pass
    
    @app_commands.command(name="post-fix", description="Sync current staff members with the database")
    @app_commands.describe(post="The position to fix")
    @app_commands.autocomplete(post=staff_position_autocomplete)
    async def post_fix(self, interaction: discord.Interaction, post: str):
        guild_config = await self.bot.staff_db.get_config(interaction.guild)

        if interaction.user.id != interaction.guild.owner.id and interaction.user.id not in guild_config['owners'] and interaction.user.id not in guild_config['staff_manager']:
            return await interaction.response.send_message(f"Only `{interaction.guild.name}'s` owners can use this command", ephemeral=True)
    
        if post not in guild_config['positions'].keys():
            return await interaction.response.send_message(f"Position `{post.capitalize()}` does not exist", ephemeral=True)
        
        post_role = interaction.guild.get_role(guild_config['positions'][post]['role'])
        if post_role is None: return await interaction.response.send_message(f"`{post.capitalize()}` role does not exist", ephemeral=True)

        await interaction.response.send_message(embed=discord.Embed(description="Please wait while we fix the post...", color=self.bot.default_color))

        added_users = []
        removed_users = []

        for member in post_role.members:
            user_data = await self.bot.staff_db.get_staff(member)
            if post not in user_data['positions'].keys():
                user_data['positions'][post] = {'name': post, 'appointed_by': interaction.user.id, 'appointed_at': datetime.datetime.utcnow()}
                await self.bot.staff_db.staff_collection.update(member.id, user_data)
                added_users.append(member.mention)
        
        staff_members = await self.bot.staff_db.staff_collection.get_all()
        for staff_member in staff_members:
            user = interaction.guild.get_member(staff_member['_id'])
            if user is None: await self.bot.staff_db.staff_collection.delete(staff_member['_id'])

            if post in staff_member['positions'].keys():
                if post_role not in user.roles:
                    del staff_member['positions'][post]
                    await self.bot.staff_db.staff_collection.update(staff_member['_id'], staff_member)
                    removed_users.append(user.mention)
        
        embed = discord.Embed(title="Post Fix", description=f"Successfully fixed `{post.capitalize()}`", color=self.bot.default_color)
        embed.add_field(name="Added Users", value=", ".join(added_users) if len(added_users) > 0 else "None", inline=False)
        embed.add_field(name="Removed Users", value=", ".join(removed_users) if len(removed_users) > 0 else "None", inline=False)
        await interaction.edit_original_response(embed=embed)

    @app_commands.command(name="revoke", description="Revoke a user's position")
    @app_commands.describe(user="The user to revoke", position="The position to revoke")
    @app_commands.autocomplete(position=staff_position_autocomplete)
    async def revoke(self, interaction: discord.Interaction, user: discord.Member, position: str):
        guild_config = await self.bot.staff_db.get_config(interaction.guild)
        
        if interaction.user.id != interaction.guild.owner.id and interaction.user.id not in guild_config['owners'] and interaction.user.id not in guild_config['staff_manager']:
            return await interaction.response.send_message(f"Only `{interaction.guild.name}'s` owners can use this command", ephemeral=True)

        if position not in guild_config['positions'].keys():
            return await interaction.response.send_message(f"Position `{position.capitalize()}` does not exist", ephemeral=True)
        
        await interaction.response.send_message(embed=discord.Embed(description="Please wait while we revoke the member...", color=self.bot.default_color))

        post = guild_config['positions'][position]
        if post['owner_only'] == True:
            if interaction.user.id != interaction.guild.owner.id and interaction.user.id not in guild_config['owners']:
                return await interaction.edit_original_response(embed=discord.Embed(description=f"Only `{interaction.guild.name}'s` owners can revoke from `{position.capitalize()}`", color=self.bot.default_color))

        user_data = await self.bot.staff_db.get_staff(user)
        if post['name'] not in user_data['positions'].keys():
            return await interaction.edit_original_response(embed=discord.Embed(description=f"{user.mention} is not in `{post['name'].capitalize()}`", color=self.bot.default_color))
        
        post_role = interaction.guild.get_role(post['role'])
        if post_role is None:
            return await interaction.edit_original_response(embed=discord.Embed(description=f"`{post['name'].capitalize()}` role does not exist", color=self.bot.default_color))
        await user.remove_roles(post_role, reason=f"Revoked from {post['name'].capitalize()} by {interaction.user}")
        del user_data['positions'][post['name']]
        if len(user_data['positions'].keys()) == 0:
            await self.bot.staff_db.staff_collection.delete(user.id)
            await interaction.edit_original_response(embed=discord.Embed(description=f"{user.mention} is now not appointed to any position", color=self.bot.default_color))
        else:
            await self.bot.staff_db.staff_collection.update(user.id, user_data)
            await interaction.edit_original_response(embed=discord.Embed(description=f"Successfully revoked {user.mention} from `{post['name'].capitalize()}`", color=self.bot.default_color))
    
    @app_commands.command(name="positions", description="View all positions")
    async def positions(self, interaction: discord.Interaction):
        guild_config = await self.bot.staff_db.get_config(interaction.guild)
        staffs = await self.bot.staff_db.staff_collection.get_all()
        pages = []
        for position in guild_config['positions'].keys():
            post = guild_config['positions'][position]
            post_role = interaction.guild.get_role(post['role'])
            if post_role is None:
                continue
            embed = discord.Embed(title=f"{post['name'].capitalize()}", color=self.bot.default_color, description="")
            embed.description += f"**Owner Only:** {post['owner_only']}\n"
            embed.description += f"**Role:** {post_role.mention}\n"
            appointed_user = [
                f"<@{user['_id']}>"
                for user in staffs if position in user['positions'].keys()
            ]
            embed.description += f"**Appointed Users:** {', '.join(appointed_user) if len(appointed_user) > 0 else '`None`'}"
            pages.append(embed)

        await Paginator(interaction=interaction, pages=pages).start(embeded=True, quick_navigation=False)

    @leave.command(name="set", description="Set the leave for staff member")
    @app_commands.describe(user="The user to set leave for", reason="The reason for leave", time="duration of leave")
    async def set(self, interaction: discord.Interaction, user: discord.Member, reason: str, time: app_commands.Transform[int, TimeConverter]):
        guild_config = await self.bot.staff_db.get_config(interaction.guild)
        
        if interaction.user.id != interaction.guild.owner.id and interaction.user.id not in guild_config['owners'] and interaction.user.id not in guild_config['staff_manager']:
            return await interaction.response.send_message(f"Only `{interaction.guild.name}'s` owners can use this command", ephemeral=True)

        await interaction.response.send_message(embed=discord.Embed(description="Please wait while we set the leave...", color=self.bot.default_color))

        user_data = await self.bot.staff_db.get_staff(user)
        
        user_data['leave']['reason'] = reason
        user_data['leave']['time'] = time
        user_data['leave']['last_leave'] = datetime.datetime.utcnow()
        user_data['leave']['on_leave'] = True

        await self.bot.staff_db.staff_collection.update(user.id, user_data)
        await interaction.edit_original_response(embed=discord.Embed(description=f"Successfully set leave for {user.mention}", color=self.bot.default_color))
        for position in user_data['positions'].keys():
            post = guild_config['positions'][position]
            post_role = interaction.guild.get_role(post['role'])
            if post_role is None:
                continue
            await user.remove_roles(post_role, reason=f"Leave from {post['name'].capitalize()} by {interaction.user}")
        
        leave_role = interaction.guild.get_role(guild_config['leave_role'])
        if leave_role is not None: await user.add_roles(leave_role, reason=f"Leave from {interaction.guild.name} by {interaction.user}")
        leave_channel = interaction.guild.get_channel(guild_config['leave_channel'])
        time = round((datetime.datetime.now() + datetime.timedelta(seconds=time)).timestamp())
        embed = discord.Embed(title=f"{user.name} is on leave", color=self.bot.default_color,description=f"**Reason:** {reason}\n**Time:** <t:{time}:R>\n**Aproved by:** {interaction.user.mention}")
        if leave_channel is not None: 
            msg = await leave_channel.send(embed=embed)
            user_data['leave']['message_id'] = msg.id
            await self.bot.staff_db.staff_collection.update(user.id, user_data)
    
    @leave.command(name="remove", description="Remove the leave for staff member")
    @app_commands.describe(user="The user to remove leave for")
    async def remove(self, interaction: discord.Interaction, user: discord.Member):
        guild_config = await self.bot.staff_db.get_config(interaction.guild)

        if interaction.user.id != interaction.guild.owner.id and interaction.user.id not in guild_config['owners'] and interaction.user.id not in guild_config['staff_manager']:
            return await interaction.response.send_message(f"Only `{interaction.guild.name}'s` owners can use this command", ephemeral=True)
        
        await interaction.response.send_message(embed=discord.Embed(description="Please wait while we remove the leave...", color=self.bot.default_color))

        user_data = await self.bot.staff_db.get_staff(user)
        if not user_data['leave']['on_leave']:
            return await interaction.edit_original_response(embed=discord.Embed(description=f"{user.mention} is not on leave", color=self.bot.default_color))
        
        user_data['leave']['on_leave'] = False
        await self.bot.staff_db.staff_collection.update(user.id, user_data)

        for position in user_data['positions'].keys():
            post = guild_config['positions'][position]
            post_role = interaction.guild.get_role(post['role'])
            if post_role is None:
                continue
            await user.add_roles(post_role, reason=f"Removed leave from {post['name'].capitalize()} by {interaction.user}")

        leave_role = interaction.guild.get_role(guild_config['leave_role'])
        if leave_role is not None: await user.remove_roles(leave_role, reason=f"Removed leave from {interaction.guild.name} by {interaction.user}")
        leave_channel = interaction.guild.get_channel(guild_config['leave_channel'])
        try:
            leave_message = await leave_channel.fetch_message(user_data['leave']['message_id'])
            embed = leave_message.embeds[0]
            embed.description += f"\n**Leave Ended by:** {interaction.user.mention}"
            await leave_message.edit(embed=embed)
        except:
            pass
        await interaction.edit_original_response(embed=discord.Embed(description=f"Successfully removed leave for {user.mention}", color=self.bot.default_color))
        user_data['leave']['message_id'] = None
        user_data['leave']['reason'] = None
        user_data['leave']['time'] = None
        await self.bot.staff_db.staff_collection.update(user.id, user_data)

 
async def setup(bot):
    await bot.add_cog(Staff(bot))
    