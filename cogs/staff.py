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
from typing import TypedDict
from bson import ObjectId
import bcrypt
import random
import string
import aiohttp


class Leave(TypedDict):
    reason: str
    time: int
    end_time: datetime.datetime
    on_leave: bool
    message_id: int


class Staff(TypedDict):
    _id: ObjectId | None
    user_id: int
    guild: int
    positions: dict
    leave: Leave


class Post_data(TypedDict):
    name: str
    appointed_by: int
    appointed_at: datetime.datetime


class Config(TypedDict):
    _id: int
    owners: List[int]
    positions: dict
    last_edit: datetime.datetime
    max_positions: int
    staff_manager: List[int]
    leave_role: int
    base_role: int
    leave_channel: int
    webhook_url: str


class Staff_DB:
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.mongo['Staff_Database']
        self.config = Document(self.db, "Config")
        self.staff = Document(self.db, "Staff")
        self.recovery = Document(self.db, "Recovery")

    async def get_config(self, guild: int) -> Config:
        data: Config = await self.config.find({"_id": guild})
        if not data:
            data: Config = {'_id': guild, 'owners': [], 'positions': {}, 'last_edit': datetime.datetime.utcnow(),
                            'max_positions': 0, 'staff_manager': [], 'leave_role': 0, 'base_role': 0,
                            'leave_channel': 0, 'webhook_url': ""}
            await self.config.insert(data)
        return data
    
    async def update_config(self, guild: int, data: Config):
        await self.config.update(data)
        return data

    async def get_staff(self, user: discord.Member, guild: discord.Guild) -> Staff | None:
        data = await self.staff.find({"user_id": user.id, "guild": guild.id})
        if not data:
            return None
        return data

    async def create_staff(self, user: discord.Member, guild: discord.Guild) -> Staff:
        data: Staff = {'user_id': user.id, 'guild': guild.id, 'positions': {}, 'leave': {}}
        await self.staff.insert(data)
        return data
    

    async def update_staff(self, user: discord.Member, guild: discord.Guild, data: Staff):
        await self.staff.update(data)

    async def staff_has_code(self, user: discord.Member) -> bool:
        data = await self.recovery.find({"user_id": user.id})
        if not data:
            return False
        return True

    async def verify_code(self, user: int, code: str) -> bool:
        data = await self.recovery.find({"user_id": user})
        if not data:
            return False
        if bcrypt.checkpw(code.encode('utf-8'), data['password']):
            return True
        return False

    async def gen_recovery(self, user: discord.Member | discord.User) -> str:
        salt = bcrypt.gensalt()
        password = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(10))
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        await self.recovery.insert({"user_id": user.id, "password": hashed, "salt": salt})
        return password

@app_commands.default_permissions(administrator=True)
class Staff_Commands(commands.GroupCog, name="staff"):
    def __init__(self, bot):
        self.bot = bot
        self.backend = Staff_DB(bot)
        self.bot.staff_db = self.backend

    async def post_auto(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        config = await self.backend.get_config(interaction.guild_id)
        choices = []
        for position in config['positions']:
            choices.append(app_commands.Choice(name=position, value=position))
        return choices[:24]

    leave = app_commands.Group(name="leave", description="Leave System Commands")

    @commands.Cog.listener()
    async def on_staff_update(self, webhook: str, embed: discord.Embed):
        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(webhook, session=session)
            await webhook.send(embed=embed, username="Staff System",
                               avatar_url=self.bot.user.avatar.url if self.bot.user.avatar else self.bot.user.default_avatar.url)

    @app_commands.command(name="appoint", description="Appoint a user to a position")
    @app_commands.describe(user="The user you want to appoint", position="The position you want to appoint them to")
    @app_commands.autocomplete(position=post_auto)
    @app_commands.default_permissions(administrator=True)
    async def appoint(self, interaction: discord.Interaction, user: discord.Member, position: str):
        guild_config = await self.backend.get_config(interaction.guild_id)
        if interaction.user.id not in guild_config['owners'] and interaction.user.id not in guild_config['staff_manager']:
            if interaction.user.id != interaction.guild.owner.id:
                return await interaction.response.send_message("You are not allowed to use this command",
                                                               ephemeral=True)
        if user.id in guild_config['owners']:
            return await interaction.response.send_message("You cannot appoint an owner", ephemeral=True)

        await interaction.response.send_message(
            embed=discord.Embed(description="Please wait while we appoint the user...", color=self.bot.default_color))

        if not await self.backend.staff_has_code(user):
            password = await self.backend.gen_recovery(user)
            try:
                embed = discord.Embed(title="Recovery Code", description=f"", color=self.bot.default_color)
                embed.description = "You have received a recovery code incase you lost access to your current discord account,"
                embed.description += "If you have lost access to your current discord account, you can use this code to recover your staff account,"
                embed.description += "To recover your account use the command `-recover <code>` in my DMs with account your other account."
                embed.description += "\n\n**Please keep this code safe and do not share it with anyone.**"
                embed.description += "\n**Higher staff members/owners or anyone will never ask you for this code.**"
                embed.add_field(name="Recovery Code", value=password, inline=False)
                await user.send(embed=embed)
                await interaction.followup.send(f"Successfully sent recovery code to {user.mention}", ephemeral=True)
            except discord.HTTPException:
                await interaction.followup.send(
                    f"Failed to send recovery code to {user.mention}, please make sure they have DMs enabled",
                    ephemeral=True)
                
        user_data = await self.backend.get_staff(user, interaction.guild)
        if not user_data:
            user_data = await self.backend.create_staff(user, interaction.guild)

        if position in user_data['positions']:
            return await interaction.response.send_message("This user already has this position", ephemeral=True)

        postdate: Post_data = {'name': position, 'appointed_by': interaction.user.id,
                               'appointed_at': datetime.datetime.utcnow()}
        user_data['positions'][position] = postdate
        post = guild_config['positions'][position]
        await user.add_roles(interaction.guild.get_role(post['role']), reason="Appointed to position")
        await user.add_roles(interaction.guild.get_role(guild_config['base_role']), reason="Appointed to position")
        await self.backend.update_staff(user, interaction.guild, user_data)

        if guild_config['webhook_url']:
            embed = discord.Embed(title="Staff Update", description=f"{user.mention} was appointed to {position}",
                                  color=self.bot.default_color)
            embed.add_field(name="Appointed By", value=interaction.user.mention, inline=False)
            embed.add_field(name="Appointed At", value=postdate['appointed_at'].strftime("%d/%m/%Y %H:%M:%S"),
                            inline=False)
            self.bot.dispatch("staff_update", guild_config['webhook_url'], embed)
        
        await interaction.edit_original_response(
            embed=discord.Embed(description=f"Successfully appointed {user.mention} to `{position.capitalize()}`",
                                color=self.bot.default_color))

    @app_commands.command(name="demote", description="Demote a user from a position")
    @app_commands.describe(user="The user you want to demote", position="The position you want to demote them from")
    @app_commands.autocomplete(position=post_auto)
    @app_commands.default_permissions(administrator=True)
    async def demote(self, interaction: discord.Interaction, user: discord.Member, position: str):
        guild_config = await self.backend.get_config(interaction.guild_id)

        if interaction.user.id != interaction.guild.owner.id and interaction.user.id not in guild_config['owners'] and interaction.user.id not in guild_config['staff_manager']:
            return await interaction.response.send_message("You are not allowed to use this command",
                                                           ephemeral=True)

        if position not in guild_config['positions'].keys():
            return await interaction.response.send_message(f"Position `{position.capitalize()}` does not exist",
                                                           ephemeral=True)

        embed = discord.Embed(description="Please wait while we demote the user...", color=self.bot.default_color)
        await interaction.response.send_message(embed=embed)

        post = guild_config['positions'][position]
        if post['owner_only']:
            if interaction.user.id != interaction.guild.owner.id and interaction.user.id not in guild_config['owners']:
                return await interaction.edit_original_response(embed=discord.Embed(
                    description=f"Only `{interaction.guild.name}'s` owners can revoke from `{position.capitalize()}`",
                    color=self.bot.default_color))

        user_data = await self.backend.get_staff(user, interaction.guild)
        if not user_data:
            return await interaction.edit_original_response(
                embed=discord.Embed(description=f"{user.mention} is not apart of any positions",
                                    color=self.bot.default_color))
        
        if post['name'] not in user_data['positions'].keys():
            return await interaction.edit_original_response(
                embed=discord.Embed(description=f"{user.mention} does not have the position `{position.capitalize()}`",
                                    color=self.bot.default_color))

        post_role = interaction.guild.get_role(post['role'])
        base_role = interaction.guild.get_role(guild_config['base_role'])

        if post_role is None:
            return await interaction.edit_original_response(
                embed=discord.Embed(description=f"`{post['name'].capitalize()}` role does not exist",
                                    color=self.bot.default_color))
        
        await user.remove_roles(post_role, reason=f"Revoked from {post['name'].capitalize()} by {interaction.user}")
        del user_data['positions'][post['name']]
        await self.backend.update_staff(user, interaction.guild, user_data)

        if len(user_data['positions']) == 0:
            await user.remove_roles(base_role, reason="Revoked from all positions")
            await interaction.edit_original_response(
                embed=discord.Embed(description=f"{user.mention} is no longer apart of any staff positions",
                                     color=self.bot.default_color))
            
            await self.backend.staff.delete(user_data)
        else:
            await interaction.edit_original_response(
                embed=discord.Embed(description=f"{user.mention} was revoked from `{position.capitalize()}`",
                                     color=self.bot.default_color))
            await self.backend.staff.update(user_data)

        if guild_config['webhook_url']:
            embed = discord.Embed(title="Staff Update", description=f"{user.mention} was revoked from {position}",
                                  color=self.bot.default_color)
            embed.add_field(name="Revoked By", value=interaction.user.mention, inline=False)
            self.bot.dispatch("staff_update", guild_config['webhook_url'], embed)

    @app_commands.command(name="positions", description="View all positions")
    @app_commands.default_permissions(administrator=True)
    async def positions(self, interaction: discord.Interaction):
        guild_config = await self.backend.get_config(interaction.guild_id)
        staffs = await self.backend.staff.find_many_by_custom({"guild": interaction.guild_id})
        pages: list[discord.Embed] = []
        for position in guild_config['positions'].keys():
            post = guild_config['positions'][position]
            embed = discord.Embed(title=f"{position.capitalize()} Position", color=self.bot.default_color,
                                  description="")
            embed.description += "**Owner Only:** " + str(guild_config['positions'][position]['owner_only']) + "\n"
            post_role = interaction.guild.get_role(post['role'])
            if post_role is None:
                continue

            embed.description += f"**Role:** {post_role.mention}\n"
            appointed_user = [
                f"<@{user['user_id']}>"
                for user in staffs if position in user['positions'].keys()
            ]
            if len(appointed_user) == 0:
                appointed_user = ["`None`"]
            embed.description += f"**Appointed Users:** {', '.join(appointed_user)}"
            pages.append(embed)
        await Paginator(interaction=interaction, pages=pages).start(embeded=True)

    @app_commands.command(name="sync", description="Remove members from positions if they do not have the role")
    @app_commands.describe(position="The position you want to sync")
    @app_commands.autocomplete(position=post_auto)
    @app_commands.default_permissions(administrator=True)
    async def sync(self, interaction: discord.Interaction, position: str):
        guild_config = await self.backend.get_config(interaction.guild_id)
        if interaction.user.id != interaction.guild.owner.id and interaction.user.id not in guild_config['owners'] and interaction.user.id not in guild_config['staff_manager']:
            return await interaction.response.send_message("You are not allowed to use this command",
                                                           ephemeral=True)
        
        if position not in guild_config['positions'].keys():
            return await interaction.response.send_message(f"Position `{position.capitalize()}` does not exist",
                                                           ephemeral=True)
        
        post = guild_config['positions'][position]
        role = interaction.guild.get_role(post['role'])
        staffs = await self.backend.staff.find_many_by_custom({"guild": interaction.guild_id})
        await interaction.response.send_message(
            embed=discord.Embed(description="Please wait while we sync the position...", color=self.bot.default_color))
        embed = discord.Embed(title=f"Syncing {position}", color=self.bot.default_color, description="**Removed Members:**\n")
        await interaction.edit_original_response(embed=embed)
        for staff in staffs:
            if position in staff['positions'].keys():
                user = interaction.guild.get_member(staff['user_id'])
                if not user:
                    embed.description += f"<@{staff['user_id']}> | User not found\n"
                    await self.backend.staff.delete(staff)
                    await interaction.edit_original_response(embed=embed)
                    continue
                if role not in user.roles:
                    if staff['leave']['on_leave']: 
                        continue
                    embed.description += f"{user.mention} | Role Removed\n"
                    await user.remove_roles(role, reason="Sync")
                    await interaction.edit_original_response(embed=embed)
                    continue
        embed.description += "**Sync Complete**"
        await interaction.edit_original_response(embed=embed)

    @leave.command(name="set", description="Set leave for your staff members")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(user="The user you want to set leave for", time="The time you want to set leave for",
                           reason="The reason you want to set leave for")
    async def set_leave(self, interaction: discord.Interaction, user: discord.Member,
                        time: app_commands.Transform[int, TimeConverter], reason: str):
        guild_config = await self.backend.get_config(interaction.guild_id)

        if interaction.user.id != interaction.guild.owner.id and interaction.user.id not in guild_config['owners'] and interaction.user.id not in guild_config['staff_manager']:
            return await interaction.response.send_message("You are not allowed to use this command",
                                                           ephemeral=True)

        await interaction.response.send_message(
            embed=discord.Embed(description="Please wait while we set leave...", color=self.bot.default_color))

        user_data = await self.backend.get_staff(user, interaction.guild)
        if not user_data:
            user_data = await self.backend.create_staff(user, interaction.guild)
        leave_data: Leave = {'reason': reason, 'time': time,
                             'end_time': datetime.datetime.utcnow() + datetime.timedelta(
                                 seconds=time), 'on_leave': True}
        user_data['leave'] = leave_data
        await self.backend.update_staff(user, interaction.guild, user_data)

        leave_role = interaction.guild.get_role(guild_config['leave_role'])
        base_role = interaction.guild.get_role(guild_config['base_role'])

        for post in user_data['positions']:
            post_role = interaction.guild.get_role(guild_config['positions'][post]['role'])
            if post_role is None:
                continue
            await user.remove_roles(post_role, reason="On leave")

        await user.add_roles(leave_role, reason="On leave")
        await user.remove_roles(base_role, reason="On leave")

        if not base_role or not leave_role:
            return await interaction.edit_original_response(
                embed=discord.Embed(description="Leave role or base role does not exist", color=self.bot.default_color))

        leave_channel = interaction.guild.get_channel(guild_config['leave_channel'])
        time = int((datetime.datetime.utcnow() + datetime.timedelta(seconds=time)).timestamp())
        embed = discord.Embed(title="Leave", color=self.bot.default_color,
                              description=f"**Staff:** {user.mention}\n**Reason:** {reason}\n**Time:** <t:{time}:R> (<t:{time}:f>)\n**Started By:** {interaction.user.mention}")
        embed.description += "\n**Positions:** "
        embed.description += ", ".join([f"`{post.capitalize()}`" for post in user_data['positions']])

        if leave_channel:
            msg = await leave_channel.send(embed=embed)
            leave_data['message_id'] = msg.id
            await self.backend.update_staff(user, interaction.guild, user_data)

        await interaction.edit_original_response(
            embed=discord.Embed(description=f"Successfully set leave for {user.mention}",
                                color=self.bot.default_color))

    @leave.command(name="remove", description="Remove leave for your staff members")
    @app_commands.describe(user="The user you want to remove leave for")
    @app_commands.default_permissions(administrator=True)
    async def remove_leave(self, interaction: discord.Interaction, user: discord.Member):
        guild_config = await self.backend.get_config(interaction.guild_id)

        if interaction.user.id != interaction.guild.owner.id and interaction.user.id not in guild_config['owners'] and interaction.user.id not in guild_config['staff_manager']:
            return await interaction.response.send_message("You are not allowed to use this command",
                                                           ephemeral=True)

        await interaction.response.send_message(
            embed=discord.Embed(description="Please wait while we remove leave...", color=self.bot.default_color))

        user_data = await self.backend.get_staff(user, interaction.guild)
        if not user_data:
            return await interaction.edit_original_response(
                embed=discord.Embed(description=f"{user.mention} is not apart of any positions",
                                    color=self.bot.default_color))
        
        for post in user_data['positions']:
            post_role = interaction.guild.get_role(guild_config['positions'][post]['role'])
            if post_role is None:
                continue
            await user.add_roles(post_role, reason="Removed from leave")

        base_role = interaction.guild.get_role(guild_config['base_role'])
        leave_role = interaction.guild.get_role(guild_config['leave_role'])

        await user.remove_roles(leave_role, reason="Removed from leave")
        await user.add_roles(base_role, reason="Removed from leave")

        try:
            leave_channel = interaction.guild.get_channel(guild_config['leave_channel'])
            if leave_channel:
                message = await leave_channel.fetch_message(user_data['leave']['message_id'])
                embed = message.embeds[0]
                embed.description += "\n**Ended By:** " + interaction.user.mention
                await message.edit(embed=embed)
        except discord.HTTPException:
            pass
        except KeyError:
            pass

        user_data['leave'] = {}
        await self.backend.update_staff(user, interaction.guild, user_data)
        await interaction.edit_original_response(
            embed=discord.Embed(description=f"Successfully removed leave for {user.mention}",
                                color=self.bot.default_color))


    @app_commands.command(name="info", description="View information about a staff member")
    @app_commands.describe(user="The user you want to view information about")
    async def info(self, interaction: discord.Interaction, user: discord.Member):
        guild_config = await self.backend.get_config(interaction.guild_id)

        if interaction.user.id != interaction.guild.owner.id and interaction.user.id not in guild_config['owners'] and interaction.user.id not in guild_config['staff_manager']:
            return await interaction.response.send_message("You are not allowed to use this command",
                                                           ephemeral=True)
        
        user_data = await self.backend.get_staff(user, interaction.guild)
        if not user_data:
            return await interaction.response.send_message(f"{user.mention} is not apart of any positions",
                                                           ephemeral=True)
        print(user_data)
        embed = discord.Embed(title="", color=self.bot.default_color, description="")
        embed.set_author(name=user.name, icon_url=user.avatar.url if user.avatar else user.default_avatar.url)
        for post in user_data['positions']:
            post_role = interaction.guild.get_role(guild_config['positions'][post]['role'])
            if post_role is None:
                continue
            embed.add_field(name=" ", value=f"**Position:** {post.capitalize()}\n**Appointed By:** <@{user_data['positions'][post]['appointed_by']}>\n**Appointed At:** {user_data['positions'][post]['appointed_at'].strftime('%d/%m/%Y %H:%M:%S')}", inline=True)

        if user_data['leave'] != {}:
            if user_data['leave']['on_leave']:
                embed.description += f"**Leave Reason:** {user_data['leave']['reason']}\n"
                embed.description += f"**Leave Time:** {user_data['leave']['time']}\n"
                embed.description += f"**Leave End Time:** {user_data['leave']['end_time'].strftime('%d/%m/%Y %H:%M:%S')}\n"

        await interaction.response.send_message(embed=embed)


    @commands.command(name="recover", description="Verify your indentitiy by using your recovery code")
    @commands.dm_only()
    async def recover(self, ctx: commands.Context, id: str, code: str):
        _id: int = int(id)
        if _id == ctx.author.id:
            return await ctx.send("You can only use this command from other account to verifying your identity from other account")
        if not await self.backend.verify_code(_id, code):
            return await ctx.send("Either the code or ID is incorrect")
        try:
            user = await self.bot.fetch_user(_id)
        except discord.NotFound:
            return await ctx.send("User not found")
        embed = discord.Embed(title="Recovery Code", description=f"", color=self.bot.default_color)
        embed.description += "You have successfully verified your old account which is mentioned below,\n"
        
        embed2 = discord.Embed()
        embed2.set_author(name=user, icon_url=user.avatar.url if user.avatar else user.default_avatar.url)
        embed2.description = f"**ID:** {_id}\n**Mention:** <@{user.id}>"
        embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
        await ctx.send(embeds=[embed, embed2])
        await self.backend.recovery.delete({"user_id": _id})

async def setup(bot):
    await bot.add_cog(Staff_Commands(bot))

