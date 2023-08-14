import enum
import discord
import datetime
from discord import Interaction, SelectOption, TextStyle, app_commands
from discord.interactions import Interaction
from discord.ui import View, Button, button, TextInput, Item, Select, select
from humanfriendly import format_timespan
from .selects import Role_select, Select_General, Channel_select, User_Select
from .modal import General_Modal
from .buttons import Confirm
from utils.converters import TimeConverter
import traceback


class ButtonCooldown(app_commands.CommandOnCooldown):
    def __init__(self, retry_after: float):
        self.retry_after = retry_after

    def key(interaction: discord.Interaction):
        return interaction.user

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
    
    async def on_error(self, interaction: Interaction, error: Exception, item: Item):
        raise error
    
    async def update_embed(self, interaction: Interaction, data):
        embed = discord.Embed(title=f"{interaction.guild.name} Perk Config", color=interaction.client.default_color, description="")
        embed.description += f"Custom Channel Category:\n"
        embed.description += "\t".join(
            [ f"<:invis_space:1067363810077319270> {cat.mention}: (10/{len(cat.channels)})\n" for cat in [interaction.guild.get_channel(cat) for cat in data['custom_category']['cat_list']] if cat != None]
        ) if len(data['custom_category']['cat_list']) > 0 else "`None`"
        embed.description += f"Custom Roles Position: `{data['custom_roles_position']}`\n"
        embed.description += f"Admin Roles: {', '.join([f'<@&{role}>' for role in data['admin_roles']]) if len(data['admin_roles']) > 0 else '`None`'}\n"
        return embed

    async def switch(self, interaction: Interaction, data: dict):
        embed = discord.Embed(title=f"{interaction.guild.name} Perk Config", color=interaction.client.default_color)
        role_profiles = data['profiles']['roles']
        channel_profiles = data['profiles']['channels']
        reaction_profiles = data['profiles']['reacts']
        hilights_profiles = data['profiles']['highlights']

        role_vales = ""
        for key, item in role_profiles.items():
            role_vales += f"<@&{key}>\n"
            role_vales += f"* **Duration:** Prmanent\n" if item['duration'] == "permanent" else f"* **Duration:** `{format_timespan(item['duration'])}`\n"
            role_vales += f"* **Friend Limit:** `{item['friend_limit']}`\n"
        embed.add_field(name="Role Profiles", value=role_vales if role_vales else "`No Profiles ;(`", inline=True)

        channel_values = ""
        for key, item in channel_profiles.items():
            channel_values += f"<@&{key}>\n"
            channel_values += f"* **Duration:** Permanent\n" if item['duration'] == "permanent" else f"* **Duration:** `{format_timespan(item['duration'])}`\n"
            channel_values += f"* **Friend Limit:** `{item['friend_limit']}`\n"
        embed.add_field(name="Channel Profiles", value=channel_values if channel_values else "`No Profiles ;(`", inline=True)

        reaction_values = ""
        for key, item in reaction_profiles.items():
            reaction_values += f"<@&{key}>\n"
            reaction_values += f"* **Duration:** Permanent\n" if item['duration'] == "permanent" else f"* **Duration:** `{format_timespan(item['duration'])}`\n"
            reaction_values += f"* **Emoji Limit:** `{item['friend_limit']}`\n"
        embed.add_field(name="Reaction Profiles", value=reaction_values if reaction_values else "`No Profiles ;(`", inline=True)

        hilight_values = ""
        for key, item in hilights_profiles.items():
            hilight_values += f"<@&{key}>\n"
            hilight_values += f"* **Duration:** Permanent\n" if item['duration'] == "permanent" else f"* **Duration:** `{format_timespan(item['duration'])}`\n"
            hilight_values += f"* **Trigger Limit:** `{item['friend_limit']}`\n"
        embed.add_field(name="Hilight Profiles", value=hilight_values if hilight_values else "`No Profiles ;(`", inline=True)

        await self.message.edit(embed=embed, view=Profile(self.user, data, self.message))        
        self.stop()
    
    @button(label="Custom Category", style=discord.ButtonStyle.gray, emoji="<:tgk_category:1076602579846447184>")
    async def custom_category(self, interaction: Interaction, button: Button):
        view = General_Modal(title="Custom Category", interaction=interaction)
        view.name = TextInput(label="Enter the name of the category",min_length=1, max_length=100, required=True)
        view.add_item(view.name)
        await interaction.response.send_modal(view)
        await view.wait()
        if view.name.value:
            if self.data['custom_category']['name'] == None:
                cat = await interaction.guild.create_category_channel(name=f"{view.name.value} - 1")
                self.data['custom_category']['last_cat'] = cat.id
                self.data['custom_category']['cat_list'].append(cat.id)
            self.data['custom_category']['name'] = view.name.value            
            await interaction.client.Perk.update("config", self.data)
            await view.interaction.response.edit_message(embed=await self.update_embed(interaction, self.data))
            for cat in self.data['custom_category']['cat_list']:
                cat = interaction.guild.get_channel(cat)
                if cat:
                    await cat.edit(name=f"{self.data['custom_category']['name']} - {self.data['custom_category']['cat_list'].index(cat.id) + 1}")

        
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

    @button(label="Profiles", style=discord.ButtonStyle.gray, emoji="<:tgk_staff_post:1074264610015826030>")
    async def profiles(self, interaction: Interaction, button: Button):
        await self.switch(interaction, self.data)
        await interaction.response.send_message("Switched to profiles", ephemeral=True)



class Profile(View):
    def __init__(self, user: discord.Member, data: dict, message: discord.Message=None):
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
        for child in self.children:child.disabled = True; 
        try:await self.message.edit(view=self)
        except:pass

    async def on_error(self, interaction: Interaction, error: Exception, item: Item):
        try:
            await interaction.followup.send(embed=discord.Embed(description=f"```py\n{traceback.format_exception(type(error), error, error.__traceback__, 4)}\n```", color=discord.Color.red()), ephemeral=True)
        except discord.HTTPException:
            raise error
    
    async def update_embed(self, interaction: Interaction, data):
        embed = discord.Embed(title=f"{interaction.guild.name} Perk Config", color=interaction.client.default_color)
        role_profiles = data['profiles']['roles']
        channel_profiles = data['profiles']['channels']
        reaction_profiles = data['profiles']['reacts']
        hilights_profiles = data['profiles']['highlights']

        role_vales = ""
        for key, item in role_profiles.items():
            role_vales += f"<@&{key}>\n"
            role_vales += f"* **Duration:** Prmanent\n" if item['duration'] == "permanent" else f"* **Duration:** `{format_timespan(item['duration'])}`\n"
            role_vales += f"* **Friend Limit:** `{item['friend_limit']}`\n"
        embed.add_field(name="Role Profiles", value=role_vales if role_vales else "`No Profiles ;(`", inline=True)

        channel_values = ""
        for key, item in channel_profiles.items():
            channel_values += f"<@&{key}>\n"
            channel_values += f"* **Duration:** Prmanent\n" if item['duration'] == "permanent" else f"* **Duration:** `{format_timespan(item['duration'])}`\n"
            channel_values += f"* **Friend Limit:** `{item['friend_limit']}`\n"
        embed.add_field(name="Channel Profiles", value=channel_values if channel_values else "`No Profiles ;(`", inline=True)

        reaction_values = ""
        for key, item in reaction_profiles.items():
            reaction_values += f"<@&{key}>\n"
            reaction_values += f"* **Duration:** Prmanent\n" if item['duration'] == "permanent" else f"* **Duration:** `{format_timespan(item['duration'])}`\n"
            reaction_values += f"* **Friend Limit:** `{item['friend_limit']}`\n"
        embed.add_field(name="Reaction Profiles", value=reaction_values if reaction_values else "`No Profiles ;(`", inline=True)

        hilight_values = ""
        for key, item in hilights_profiles.items():
            hilight_values += f"<@&{key}>\n"
            hilight_values += f"* **Duration:** Permanent\n" if item['duration'] == "permanent" else f"* **Duration:** `{format_timespan(item['duration'])}`\n"
            hilight_values += f"* **Trigger Limit:** `{item['friend_limit']}`\n"
        embed.add_field(name="Hilight Profiles", value=hilight_values if hilight_values else "`No Profiles ;(`", inline=True)

        await self.message.edit(embed=embed, view=Profile(self.user, data, self.message))
    
    async def switch(self, interaction: Interaction, data: dict):
        embed = discord.Embed(title=f"{interaction.guild.name} Perk Config", color=interaction.client.default_color, description="")
        embed.description += f"Custom Channel Category:\n"
        embed.description += "\t".join(
            [ f"<:invis_space:1067363810077319270> {cat.mention}: (10/{len(cat.channels)})\n" for cat in [interaction.guild.get_channel(cat) for cat in data['custom_category']['cat_list']] if cat != None]
        ) if len(data['custom_category']['cat_list']) > 0 else "`None`\n"
        embed.description += f"Custom Roles Position: `{data['custom_roles_position']}`\n"
        embed.description += f"Admin Roles: {', '.join([f'<@&{role}>' for role in data['admin_roles']]) if len(data['admin_roles']) > 0 else '`None`'}\n"
        await self.message.edit(embed=embed, view=PerkConfig(self.user, data, self.message))
        self.stop()


    @button(label="Manage Profiles", style=discord.ButtonStyle.gray, emoji="<:tgk_role:1073908306713780284>")
    async def role_profiles(self, interaction: Interaction, button: Button):
        profile_select = View()
        profile_select.value = None
        profile_select.select = Select_General(placeholder="Select a profile type", options=[
            SelectOption(label="Roles", description="Manage role profiles", emoji="<:tgk_role:1073908306713780284>", value="roles"),
            SelectOption(label="Channels", description="Manage channel profiles", emoji="<:tgk_channel:1073908465405268029>", value="channels"),
            SelectOption(label="Reactions", description="Manage reaction profiles", emoji="<:tgk_color:1107261678204244038>", value="reacts"),
            SelectOption(label="highlights", description="Manage hilight profiles", emoji="<:tgk_message:1113527047373979668>", value="highlights"),
        ], max_values=1, min_values=1)
        profile_select.add_item(profile_select.select)
        await interaction.response.send_message(view=profile_select, ephemeral=True)
        await profile_select.wait()
        if profile_select.value != True: await profile_select.select.interaction.delete_original_response()
        profile = profile_select.select.values[0]

        view = View()
        view.value = None
        view.select = Select_General(placeholder="Select a Operation", options=[
            SelectOption(label="Add Profile", description="Add a new role profile", emoji="<:tgk_add:1073902485959352362>", value="add"),
            SelectOption(label="Delete Profile", description="Delete a role profile", emoji="<:tgk_delete:1113517803203461222>", value="delete"),
        ], max_values=1, min_values=1)
        view.add_item(view.select)
        await profile_select.select.interaction.response.edit_message(view=view)
        await view.wait()
        if view.value != True: await view.select.interaction.delete_original_response()

        match view.select.values[0]:

            case "add":
                role_view = View()
                role_view.select = Role_select(placeholder="Select a role for which you want to add a profile", max_values=1, min_values=1)
                role_view.value = False
                role_view.add_item(role_view.select)
                await view.select.interaction.response.edit_message(view=role_view)
                await role_view.wait()

                if role_view.value != True: await view.select.interaction.delete_original_response()

                profile_data = {
                    "role_id": None,
                    "duration": 0,
                    "friend_limit": 0
                }
                role = role_view.select.values[0]
                if str(role.id) in self.data['profiles'][profile].keys():
                    return await role_view.select.interaction.response.edit_message(content="This role already has a profile", view=None)
                profile_data['role_id'] = role.id
                friend_view = View()
                friend_view.value = False
                friend_view.select = Select_General(placeholder="Select a friend limit", options=[
                        SelectOption(label=str(i), value=i) 
                        for i in range(1, 10)
                    ]
                )
                friend_view.add_item(friend_view.select)
                await role_view.select.interaction.response.edit_message(view=friend_view)

                await friend_view.wait()
                if friend_view.value != True: await view.select.interaction.delete_original_response()

                profile_data['friend_limit'] = int(friend_view.select.values[0])

                duration_view = General_Modal(title="Profile Duration", interaction=interaction)
                duration_view.duraction = TextInput(label="Enter the Duration of the profile", placeholder="Enter permanent for no duration", min_length=1, max_length=100)
                duration_view.add_item(duration_view.duraction)
                await friend_view.select.interaction.response.send_modal(duration_view)

                await duration_view.wait()
                if duration_view.value != True: await view.select.interaction.delete_original_response()

                duration = duration_view.duraction.value
                if duration.lower() != "permanent":
                    duration = await TimeConverter().convert(interaction, duration)
                    if duration is None:
                        return await duration_view.duraction.interaction.response.send_message("Invalid duration", ephemeral=True)
                profile_data['duration'] = duration

                embed = discord.Embed(title="Profile Preview", color=interaction.client.default_color, description="")
                embed.description += f"**Role:** <@&{profile_data['role_id']}>\n"
                embed.description += f"**Duration:** Permanent\n" if profile_data['duration'] == "permanent" else f"**Duration:** {format_timespan(profile_data['duration'])}\n"
                embed.description += f"**Friend Limit:** `{profile_data['friend_limit']}`\n"
                confirm = Confirm(interaction.user, 30)
                confirm.children[0].label = "Save"; confirm.children[0].style = discord.ButtonStyle.gray; confirm.children[0].emoji = "<:tgk_active:1082676793342951475>"
                confirm.children[1].label = "Cancel"; confirm.children[1].style = discord.ButtonStyle.gray; confirm.children[1].emoji = "<:tgk_deactivated:1082676877468119110>"
                await duration_view.interaction.response.edit_message(embed=embed, view=confirm)
                confirm.message = await duration_view.interaction.original_response()
                await confirm.wait()

                if confirm.value != True: await view.select.interaction.delete_original_response()
                self.data['profiles'][profile][str(role.id)] = profile_data
                await view.select.interaction.client.Perk.update("config", self.data)
                await self.update_embed(confirm.interaction, self.data)
    
        
            case "delete":
                role_prof = View()
                role_prof.value = True
                options = []
                for key, item in self.data['profiles'][profile].items():
                    role = interaction.guild.get_role(int(key))
                    options.append(SelectOption(label=role.name, value=key))

                role_prof.select = Select_General(placeholder="Select a role profile to delete", options=options, max_values=len(options), min_values=1)
                role_prof.add_item(role_prof.select)
                await view.select.interaction.response.edit_message(view=role_prof)
                await role_prof.wait()

                if role_prof.value != True: await view.select.interaction.delete_original_response()
                for value in role_prof.select.values:
                    del self.data['profiles'][profile][value]
                await view.select.interaction.client.Perk.update("config", self.data)
                await self.update_embed(interaction, self.data)
                await role_prof.select.interaction.response.edit_message(content="Profile deleted", view=None)

    @button(label="Back", style=discord.ButtonStyle.gray, emoji="<:tgk_leftarrow:1088526575781285929> ")
    async def back(self, interaction: Interaction, button: Button):
        await self.switch(interaction, self.data)
        await interaction.response.send_message("Switched to config", ephemeral=True)

class friends_manage(View):
    def __init__(self, user: discord.Member, data: dict, type: str,message: discord.Message=None):
        self.user = user
        self.data = data
        self.message = message
        self.type = type
        self.cd = app_commands.Cooldown(1, 10)
        if type not in ["roles", "channels"]:
            raise ValueError("type must be either roles or channels")
        super().__init__(timeout=120)
    
    async def interaction_check(self, interaction: Interaction):
        retry_after = self.cd.update_rate_limit()
        if retry_after:
            raise ButtonCooldown(retry_after)

        if interaction.user.id == self.user.id:
            return True
        else:
            await interaction.response.send_message("You are not the owner of this menu", ephemeral=True)
            return False

    async def on_timeout(self):
        for child in self.children:child.disabled = True; await self.message.edit(view=self)
    
    async def on_error(self, interaction: Interaction, error: Exception, item: Item):
        if isinstance(error, ButtonCooldown):
            seconds = int(error.retry_after)
            unit = 'second' if seconds == 1 else 'seconds'
            return await interaction.response.send_message(f"You're on cooldown for {seconds} {unit}!", ephemeral=True)
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
