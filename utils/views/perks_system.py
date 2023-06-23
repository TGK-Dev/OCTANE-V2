import enum
import discord
import datetime
from discord import Interaction, SelectOption, TextStyle
from discord.interactions import Interaction
from discord.ui import View, Button, button, TextInput, Item, Select, select
from .selects import Role_select, Select_General, Channel_select, User_Select
from .modal import General_Modal
import traceback

class PerkConfig(View):
    def __init__(self, user:discord.Member, data:dict, message: discord.Message=None):
        self.user = user
        self.data = data
        self.message = message
        super().__init__(timeout=120)
    
    async def interaction_check(self, interaction: Interaction):
        if interaction.user.id == self.user.id:
            return True
        else:
            await interaction.response.send_message("You are not the owner of this perk", ephemeral=True)
            return False
    
    async def on_timeout(self):
        for child in self.children:child.disabled = True; await self.message.edit(view=self)
    
    async def on_error(self, error, item, interaction):
        raise error
    
    async def update_embed(self, interaction: Interaction, data):
        embed = discord.Embed(title=f"{interaction.guild.name} Perk Config", color=interaction.client.default_color, description="")
        embed.description += f"Custom Category: {interaction.guild.get_channel(data['custom_category']).mention if data['custom_category'] else '`None`'}\n"
        embed.description += f"Custom Roles Position: `{data['custom_roles_position']}`\n"
        embed.description += f"Admin Roles: {', '.join([f'<@&{role}>' for role in data['admin_roles']]) if len(data['admin_roles']) > 0 else '`None`'}\n"
        return embed
    
    @button(label="Custom Category", style=discord.ButtonStyle.gray, emoji="<:tgk_category:1076602579846447184>")
    async def custom_category(self, interaction: Interaction, button: Button):
        view = View()
        view.select = Channel_select(placeholder="Select a category for custom channels", max_values=1, channel_types=[discord.ChannelType.category], min_values=1)
        view.value = False
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()
        if view.value:
            self.data['custom_category'] = view.select.values[0].id
            await interaction.delete_original_response()
            await interaction.client.Perk.update("config", self.data)
            await self.message.edit(embed=await self.update_embed(interaction, self.data))
        
    @button(label="Custom Roles Position", style=discord.ButtonStyle.gray, emoji="<:tgk_role:1073908306713780284>")
    async def custom_roles_position(self, interaction: Interaction, button: Button):
        view = View()
        view.value = False
        view.select = Role_select(placeholder="Select a role to set the position of custom roles", max_values=1, min_values=1)
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()
        if view.value:
            position = view.select.values[0]
            if position >= interaction.guild.me.top_role or position >= interaction.user.top_role:
                return await view.select.interaction.response.send_message(content="You can't set the position of custom roles to a role higher than  or my top role", view=None, ephemeral=True)
            if position == interaction.guild.default_role.position:
                return await view.select.interaction.response.send_message(content="You can't set the position of custom roles to the default role", view=None, ephemeral=True)
            
            self.data['custom_roles_position'] = position.id
            await interaction.client.Perk.update("config", self.data)
            await interaction.delete_original_response()
            await self.message.edit(embed=await self.update_embed(interaction, self.data))
    
    @button(label="Admin Roles", style=discord.ButtonStyle.gray, emoji="<:tgk_admin:1073908306713780284>")
    async def admin_roles(self, interaction: Interaction, button: Button):
        view = View()
        view.value = False
        view.select = Role_select(placeholder="Select a role to add/remove from admin roles", max_values=10, min_values=1)
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()
        if view.value:
            add_roles = []
            remove_roles = []
            for value in view.select.values:
                if value.id in self.data['admin_roles']:
                    self.data['admin_roles'].remove(value.id)
                    remove_roles.append(value)
                else:
                    self.data['admin_roles'].append(value.id)
                    add_roles.append(value)
            await interaction.client.Perk.update("config", self.data)
            await view.select.interaction.response.send_message(embed=discord.Embed(description=f"Added Roles: {', '.join([role.mention for role in add_roles]) if add_roles else '`None`'}\nRemoved Roles: {', '.join([role.mention for role in remove_roles]) if remove_roles else '`None`'}", color=interaction.client.default_color), ephemeral=True, delete_after=10)

            await self.message.edit(embed=await self.update_embed(interaction, self.data))                

class friends_manage(View):
    def __init__(self, user: discord.Member, data: dict, type: str,message: discord.Message=None):
        self.user = user
        self.data = data
        self.message = message
        self.type = type
        if type not in ["roles", "channels"]:
            raise ValueError("type must be either roles or channels")
        super().__init__(timeout=120)
    
    async def interaction_check(self, interaction: Interaction):
        if interaction.user.id == self.user.id:
            return True
        else:
            await interaction.response.send_message("You are not the owner of this menu", ephemeral=True)
            return False

    async def on_timeout(self):
        for child in self.children:child.disabled = True; await self.message.edit(view=self)
    
    async def on_error(self, interaction: Interaction, error: Exception, item: Item):
        try:
            await interaction.followup.send(embed=discord.Embed(description=f"```py\n{traceback.format_exception(type(error), error, error.__traceback__, 4)}\n```", color=discord.Color.red()), ephemeral=True)
        except discord.HTTPException:
            raise error

    @select(placeholder="Select a members to add/remove from your friends", max_values=10, cls=discord.ui.UserSelect, min_values=1)
    async def select(self, interaction: Interaction, select: Select):
        add_friends = []
        remove_friends = []
        await interaction.response.send_message("Processing...", ephemeral=True)
        match self.type:
            case "roles":
                role = interaction.guild.get_role(self.data['role_id'])
                for value in select.values:
                    if value.id in self.data['friend_list'] or value in role.members:
                        remove_friends.append(value)
                        await value.remove_roles(role, reason=f"Removed from {self.user.name}'s friends")
                        try:
                            self.data['friend_list'].remove(value.id)
                        except:
                            pass
                    else:
                        if len(self.data['friend_list']) >= self.data['friend_limit']:
                            break
                        add_friends.append(value)
                        await value.add_roles(role, reason=f"Added to {self.user.name}'s friends")
                        self.data['friend_list'].append(value.id)

                res_embed = discord.Embed(title="Friends Updated", color=interaction.client.default_color, description="")
                res_embed.description += f"**Added:** {', '.join([f'<@{friend.id}>' for friend in add_friends]) if add_friends else '`None`'}\n"
                res_embed.description += f"**Removed:** {', '.join([f'<@{friend.id}>' for friend in remove_friends]) if remove_friends else '`None`'}\n"
                await interaction.edit_original_response(embed=res_embed, content=None)
                
                await interaction.client.Perk.update("roles", self.data)

                up_embed = self.message.embeds[0]
                friends = "".join([f"<@{friend}> `({friend})`\n" for friend in self.data['friend_list']])
                up_embed.set_field_at(0, name="Friends", value=friends if friends else "`No Friends ;(`", inline=False)
                await self.message.edit(embed=up_embed)
                return
            
            case "channels":
                for value in select.values:
                    value = interaction.guild.get_member(value.id)
                    channel = interaction.guild.get_channel(self.data['channel_id'])
                    if value in channel.overwrites.keys() or value.id in self.data['friend_list']:
                        remove_friends.append(value)
                        await channel.set_permissions(value, overwrite=None, reason=f"Removed from {self.user.name}'s friends")
                        try:
                            self.data['friend_list'].remove(value.id)
                        except ValueError:
                            pass
                    else:
                        if len(self.data['friend_list']) >= self.data['friend_limit']:
                            break
                        add_friends.append(value)
                        await channel.set_permissions(value, view_channel=True, reason=f"Added to {self.user.name}'s friends")
                        self.data['friend_list'].append(value.id)
                
                res_embed = discord.Embed(title="Friends Updated", color=interaction.client.default_color, description="")
                res_embed.description += f"**Added:** {', '.join([f'<@{friend.id}>' for friend in add_friends]) if add_friends else '`None`'}\n"
                res_embed.description += f"**Removed:** {', '.join([f'<@{friend.id}>' for friend in remove_friends]) if remove_friends else '`None`'}\n"
                await interaction.edit_original_response(embed=res_embed, content=None)

                await interaction.client.Perk.update("channels", self.data)

                up_embed = self.message.embeds[0]
                friends = "".join([f"<@{friend}> `({friend})`\n" for friend in self.data['friend_list']])
                up_embed.set_field_at(0, name="Friends", value=friends if friends else "`No Friends ;(`", inline=False)
                await self.message.edit(embed=up_embed)
                return
    
    @button(label="Reset Friends", style=discord.ButtonStyle.red)
    async def reset(self, interaction: Interaction, button: Button):
        match self.type:
            case "roles":
                role = interaction.guild.get_role(self.data['role_id'])
                for member in role.members:
                    if member.id != self.data['user_id']:
                        await member.remove_roles(role, reason=f"Removed from {self.user.name}'s friends")
                self.data['friend_list'] = []
                await interaction.client.Perk.update("roles", self.data)
                await interaction.response.send_message("Friends resetted", ephemeral=True)

                up_embed = self.message.embeds[0]
                friends = "".join([f"<@{friend}> `({friend})`\n" for friend in self.data['friend_list']])
                up_embed.set_field_at(0, name="Friends", value=friends if friends else "`No Friends ;(`", inline=False)
                await self.message.edit(embed=up_embed)
                return
            
            case "channels":
                channel = interaction.guild.get_channel(self.data['channel_id'])
                for friends in self.data['friend_list']:
                    member = interaction.guild.get_member(friends)
                    if member:
                        await channel.set_permissions(member, overwrite=None, reason=f"Removed from {self.user.name}'s friends")
                self.data['friend_list'] = []
                await interaction.client.Perk.update("channels", self.data)
                await interaction.response.send_message("Friends resetted", ephemeral=True)

                up_embed = self.message.embeds[0]
                friends = "".join([f"<@{friend}> `({friend})`\n" for friend in self.data['friend_list']])
                up_embed.set_field_at(0, name="Friends", value=friends if friends else "`No Friends ;(`", inline=False)
                await self.message.edit(embed=up_embed)
                return
            
            case _:
                await interaction.response.send_message("Something went wrong", ephemeral=True)
                return
    

class Perk_Ignore(discord.ui.View):
    def __init__(self, data: dict, message: discord.Message=None):
        super().__init__(timeout=120)
        self.data = data
        self.message = message
    
    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id == self.data['user_id']:
            return True
        await interaction.response.send_message("This is not your perk", ephemeral=True)
        return False

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        try:
            await self.message.edit(view=self)
        except discord.NotFound:
            pass
    
    async def get_embed(self, data: dict, interaction: discord.Interaction):
        embed = discord.Embed(title="Ignore Role/Channel", description="", color=interaction.client.default_color)
        embed.description += "Users:" + f"{', '.join([f'<@{i}>' for i in data['ignore_users']]) if data['ignore_users'] else '`None`'}"
        embed.description += "\nChannels:" + f"{', '.join([f'<#{i}>' for i in data['ignore_channel']]) if data['ignore_channel'] else '`None`'}"
        return embed
    
    @select(placeholder="Select users you want to ignore or unignore", min_values=1, max_values=25, cls=discord.ui.UserSelect)
    async def _user(self, interaction: discord.Interaction, select: Select):
        added = ""
        removed = ""
        for value in select.values:
            if value.id in self.data['ignore_users']:
                self.data['ignore_users'].remove(value.id)
                removed += f"<@{value.id}> `({value.id})`\n"
            else:
                self.data['ignore_users'].append(value.id)
                added += f"<@{value.id}> `({value.id})`\n"
        await interaction.response.edit_message(embed=await self.get_embed(self.data, interaction))
        await interaction.client.Perk.update("highlights", self.data)
        await interaction.followup.send(f"**Added:**\n{added if added else '`None`'}\n**Removed:**\n{removed if removed else '`None`'}", ephemeral=True)
    
    @select(placeholder="Select channels you want to ignore or unignore", min_values=1, max_values=25, cls=discord.ui.ChannelSelect)
    async def _channel(self, interaction: discord.Interaction, select: Select):
        added = ""
        removed = ""
        for value in select.values:
            if value.id in self.data['ignore_channel']:
                self.data['ignore_channel'].remove(value.id)
                removed += f"<#{value.id}> `({value.id})`\n"
            else:
                self.data['ignore_channel'].append(value.id)
                added += f"<#{value.id}> `({value.id})`\n"
        await interaction.response.edit_message(embed=await self.get_embed(self.data, interaction))
        await interaction.client.Perk.update("highlights", self.data)
        await interaction.followup.send(f"**Added:**\n{added if added else '`None`'}\n**Removed:**\n{removed if removed else '`None`'}", ephemeral=True)

    @button(label="Reset", style=discord.ButtonStyle.red)
    async def reset(self, interaction: Interaction, button: Button):
        self.data['ignore_users'] = []
        self.data['ignore_channel'] = []
        await interaction.client.Perk.update("highlights", self.data)
        await interaction.response.edit_message(embed=await self.get_embed(self.data, interaction))
        await interaction.followup.send("Ignored users and channels resetted\nNote: This might take a while to update", ephemeral=True)
