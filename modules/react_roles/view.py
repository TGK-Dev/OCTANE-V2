from typing import Any
import discord
from discord import app_commands, Interaction, ButtonStyle, SelectOption
from discord.ui import View, Button, Select, button, select, TextInput
from discord.ui.item import Item
from .db import RoleMenuProfile, ReactRoleMenuType, RoleMenuRoles
from utils.views.selects import Role_select, Select_General
from utils.views.modal import General_Modal

class RoleMenu_Panel(View):
    """
    Perameters
    ----------
    user: discord.Member
        User who initiated the menu
    guild: discord.Guild
        Guild where the menu was initiated
    profile: RoleMenuProfile
        Profile which the menu is for
    message: discord.Message
        The Message object where will be view attached
    """
    def __init__(self, user: discord.Member, guild: discord.Guild, profile: RoleMenuProfile, message: discord.Message=None):
        super().__init__(timeout=120)
        self.user = user
        self.guild = guild
        self.profile = profile
        self.message = None

    async def on_timeout(self):
        for cld in self.children:cld.disabled = True
        try:await self.message.edit(view=self)
        except:pass

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("You are not allowed to use this menu", ephemeral=True)
            return False
        else:
            return True
    
    async def update_embed(self):
        if not self.message:return
        embed = discord.Embed.from_dict(self.message.embeds[0].to_dict())

        req_role = []
        for data in self.profile['req_roles']:
            role = self.guild.get_role(data)
            if role:
                req_role.append(role.mention)
            else:
                self.profile['req_roles'].remove(data)
        req_role = ", ".join(req_role) if req_role else "`None`"

        bl_role = []
        for data in self.profile['bl_roles']:
            role = self.guild.get_role(data)
            if role:
                bl_role.append(role.mention)
            else:
                self.profile['bl_roles'].remove(data)
        bl_role = ", ".join(bl_role) if bl_role else "`None`"

        roles = ""
        for data in self.profile['roles'].values(): 
            role = self.guild.get_role(data['role_id'])
            if not role:
                del self.profile['roles'][data['role_id']]
                continue
            roles += f"{data['emoji']}: {role.mention}\n"
        
        embed.clear_fields()
        embed.add_field(name="Display Name", value=f"<:nat_reply:1146498277068517386> {self.profile['display_name']}", inline=False)
        embed.add_field(name="Required Role", value=f"<:nat_reply:1146498277068517386> {req_role}", inline=False)
        embed.add_field(name="Blacklisted Role", value=f"<:nat_reply:1146498277068517386> {bl_role}", inline=False)
        embed.add_field(name="Type", value=f"<:nat_reply:1146498277068517386> {str(ReactRoleMenuType(self.profile['type']))}", inline=False)
        embed.add_field(name="Roles", value=roles, inline=False)
        await self.message.edit(embed=embed)
    
    @button(label="Display Name", style=ButtonStyle.gray, emoji="<:tgk_entries:1124995375548338176>")
    async def _display_name(self, interaction: Interaction, button: Button):
        modal = General_Modal(title="Display Name", interaction=interaction)
        modal.value = None
        modal.text = TextInput(label="Enter a display name", placeholder="Display Name", max_length=100)
        modal.add_item(modal.text)
        await interaction.response.send_modal(modal)

        await modal.wait()
        if modal.value is None or False:
            return
        self.profile['display_name'] = modal.text.value
        await modal.interaction.response.send_message(content=f"Set display name to {modal.text.value}", view=None)
        await self.update_embed()

    
    @button(label="Required Role", style=ButtonStyle.gray, emoji="<:tgk_role:1073908306713780284>")
    async def _req_role(self, interaction: Interaction, button: Button):
        view = View()
        view.value = None
        view.select = Role_select(
            placeholder="Select a role you want to set as required",
            max_values=10,
            min_values=1,
        )
        view.add_item(view.select)
        await interaction.response.send_message(view=view, ephemeral=True)

        await view.wait()

        if view.value is None or False:
            await interaction.delete_original_response()
            return
        added = []
        removed = []
        for role in view.select.values:
            if role.id in self.profile['req_roles']:
                self.profile['req_roles'].remove(role.id)
                removed.append(role.mention)
            else:
                self.profile['req_roles'].append(role.id)
                added.append(role.mention)
            
        await view.select.interaction.response.edit_message(content=f"Added: {','.join(added) if len(added) != 0 else '`None`'}\nRemoved: {','.join(removed) if len(removed) != 0 else '`None`'}", view=None)

        await self.update_embed()

        await interaction.client.rm.update_profile(self.guild.id, self.profile['name'] ,self.profile)


    @button(label="Blacklisted Role", style=ButtonStyle.gray, emoji="<:tgk_role:1073908306713780284>")
    async def _bl_role(self, interaction: Interaction, button: Button):
        view = View()
        view.value = None
        view.select = Role_select(
            placeholder="Select a role you want to set as blacklisted",
            max_values=10,
            min_values=1,
        )
        view.add_item(view.select)
        await interaction.response.send_message(view=view, ephemeral=True)

        await view.wait()

        if view.value is None or False:
            await interaction.delete_original_response()
            return

        added = []
        removed = []

        for role in view.select.values:
            if role.id in self.profile['bl_roles']:
                self.profile['bl_roles'].remove(role.id)
                removed.append(role.mention)
            else:
                self.profile['bl_roles'].append(role.id)
                added.append(role.mention)
        
        await view.select.interaction.response.edit_message(content=f"Added: {','.join(added)}\nRemoved: {','.join(removed)}", view=None)

        await self.update_embed()

        await interaction.client.rm.update_profile(self.guild.id, self.profile['name'] ,self.profile)

    @button(label="Type", style=ButtonStyle.gray, emoji="<:tgk_category:1076602579846447184>")
    async def _menu_type(self, interaction: Interaction, button: Button):
        view = View()
        view.value = None
        view.select = Select_General(interaction=interaction,
            placeholder="Select a type",
            options=[
                SelectOption(label=str(ReactRoleMenuType.ADD_ONLY), value=ReactRoleMenuType.ADD_ONLY.value),
                SelectOption(label=str(ReactRoleMenuType.REMOVE_ONLY), value=ReactRoleMenuType.REMOVE_ONLY.value),
                SelectOption(label=str(ReactRoleMenuType.ADD_AND_REMOVE), value=ReactRoleMenuType.ADD_AND_REMOVE.value),
                SelectOption(label=str(ReactRoleMenuType.UNIQUE), value=ReactRoleMenuType.UNIQUE.value),
            ],
            max_values=1,
            min_values=1,
        )
        view.select.options[self.profile['type']].default = True
        view.add_item(view.select)
        await interaction.response.send_message(view=view, ephemeral=True)

        await view.wait()

        if view.value is None or False:
            await interaction.delete_original_response()
            return

        self.profile['type'] = int(view.select.values[0])

        await view.select.interaction.response.edit_message(content=f"Set type to {str(ReactRoleMenuType(self.profile['type']))}", view=None)

        await self.update_embed()

        await interaction.client.rm.update_profile(self.guild.id, self.profile['name'] ,self.profile)
    
    @button(label="Manage Roles", style=ButtonStyle.gray, emoji="<:tgk_logging:1107652646887759973>")
    async def _manage_roles(self, interaction: Interaction, button: Button):
        op_view = View()
        op_view.value = None 
        op_view.select = Select_General(interaction=interaction,
            placeholder="Select an option",
            options=[
                SelectOption(label="Add Role", value="add", description="Add a role to the menu", emoji="<:tgk_add:1073902485959352362>"),
                SelectOption(label="Remove Role", value="remove", description="Remove a role from the menu", emoji="<:tgk_minus:1163044783401467965>"),
                SelectOption(label="Clear Roles", value="clear", description="Clear all roles from the menu", emoji="<:tgk_delete:1113517803203461222>"),
            ],
            max_values=1,
            min_values=1,
        )
        op_view.add_item(op_view.select)
        await interaction.response.send_message(view=op_view, ephemeral=True)

        await op_view.wait()
        if op_view.value is None or False:
            await interaction.delete_original_response()
            return
        
        match op_view.select.values[0]:
            case "add":
                data = RoleMenuRoles(role_id=None, emoji=None)
                embed = discord.Embed(title="Add Role", description="Select a role you want to add", color=interaction.client.default_color)
                add_role = View()
                add_role.value = None
                add_role.select = Role_select(
                    placeholder="Select a role you want to add",
                    max_values=1,
                    min_values=1,
                )
                add_role.add_item(add_role.select)
                await op_view.select.interaction.response.edit_message(embed=embed, view=add_role)

                await add_role.wait()

                if add_role.value is None or False:
                    await op_view.select.interaction.delete_original_response()
                    return
                if interaction.user.top_role.position < add_role.select.values[0].position:
                    await add_role.select.interaction.response.send_message("You can't add roles higher than your top role", ephemeral=True)
                    return
                if add_role.select.values[0].position > interaction.guild.me.top_role.position:
                    await add_role.select.interaction.response.send_message("I can't add roles higher than my top role", ephemeral=True)
                    return
                
                if add_role.select.values[0].permissions.administrator or add_role.select.values[0].permissions.manage_roles or add_role.select.values[0].permissions.manage_guild or add_role.select.values[0].permissions.ban_members or add_role.select.values[0].permissions.kick_members:
                    await add_role.select.interaction.response.send_message("Due to security reason you can't add this role", ephemeral=True)
                    return

                data['role_id'] = add_role.select.values[0].id
                emoji_modal = General_Modal(title="Emoji Selection", interaction=add_role.select.interaction)
                emoji_modal.value = None
                emoji_modal.emoji = TextInput(label="Paste an emoji you want to use", placeholder="it's recommended to use custom emojis", max_length=100)
                emoji_modal.add_item(emoji_modal.emoji)

                await add_role.select.interaction.response.send_modal(emoji_modal)
                embed.description = ""
                embed.add_field(name="Role", value=add_role.select.values[0].mention, inline=False)
                embed.add_field(name="Emoji", value=emoji_modal.emoji.value, inline=False)
                await op_view.select.interaction.edit_original_response(embed=embed)

                await emoji_modal.wait()
                if emoji_modal.value is None or False:
                    await op_view.select.interaction.delete_original_response()
                    return
                data['emoji'] = emoji_modal.emoji.value
                try:                    
                    await self.message.add_reaction(data['emoji'])
                    await self.message.remove_reaction(data['emoji'], interaction.guild.me)
                except:
                    await emoji_modal.interaction.response.edit_message(content="Invalid emoji", view=None, embed=None)
                    return
                await emoji_modal.interaction.response.edit_message(content="Added role", view=None, embed=None)

                self.profile['roles'][str(data['role_id'])] = data
                await self.update_embed()
                await interaction.client.rm.update_profile(self.guild.id, self.profile['name'] ,self.profile)

            case "remove":
                remove_view = View()
                remove_view.value = None
                option = []
                for roles in self.profile['roles'].values():
                    role = self.guild.get_role(int(roles['role_id']))
                    if not role:
                        del self.profile['roles'][str(roles['role_id'])]
                        continue
                    option.append(SelectOption(label=role.name, value=role.id, emoji=roles['emoji']))
                remove_view.select = Select_General(interaction=interaction,
                    placeholder="Select role you want to remove",
                    options=option,
                    max_values=len(option),
                    min_values=1,
                )
                remove_view.add_item(remove_view.select)
                await op_view.select.interaction.response.edit_message(view=remove_view)
                await remove_view.wait()
                if remove_view.value is None or False:
                    await op_view.select.interaction.delete_original_response()
                    return      
                for role in remove_view.select.values:
                    del self.profile['roles'][str(role)]
                await remove_view.select.interaction.response.edit_message(content="Removed role(s)", view=None, embed=None)

                await self.update_embed()
            
            case "clear":
                self.profile['roles'] = {}
                await self.update_embed()
                await interaction.client.rm.update_profile(self.guild.id, self.profile['name'] ,self.profile)
                await op_view.select.interaction.response.edit_message(content="Cleared all roles", view=None, embed=None)

                await self.update_embed()

class RoleMenu_Button(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    async def callback(self, interaction: Interaction):
        data = self.custom_id.split(":")
        role = interaction.guild.get_role(int(data[3]))
        if not role:
            await interaction.response.send_message(embed=discord.Embed(description="Error: Role not Found contanct server admins", color=discord.Color.red()), ephemeral=True)
        menu: RoleMenuProfile = self.view.menu

        match menu['type']:
            case ReactRoleMenuType.ADD_ONLY.value:
                if role in interaction.user.roles:
                    await interaction.response.send_message(embed=discord.Embed(description="You already have this role", color=discord.Color.red()), ephemeral=True)
                    return
                await interaction.user.add_roles(role)
                await interaction.response.send_message(embed=discord.Embed(description=f"Added {role.mention}", color=interaction.client.default_color), ephemeral=True)
                return
            
            case ReactRoleMenuType.REMOVE_ONLY.value:
                if role not in interaction.user.roles:
                    await interaction.response.send_message(embed=discord.Embed(description="You don't have this role", color=discord.Color.red()), ephemeral=True)
                    return
                await interaction.user.remove_roles(role)
                await interaction.response.send_message(embed=discord.Embed(description=f"Removed {role.mention}", color=interaction.client.default_color), ephemeral=True)
                return
            
            case ReactRoleMenuType.ADD_AND_REMOVE.value | ReactRoleMenuType.DEFAULT:
                if role in interaction.user.roles:
                    await interaction.user.remove_roles(role)
                    await interaction.response.send_message(embed=discord.Embed(description=f"Removed {role.mention}", color=interaction.client.default_color), ephemeral=True)

                else:
                    await interaction.user.add_roles(role)
                    await interaction.response.send_message(embed=discord.Embed(description=f"Added {role.mention}", color=interaction.client.default_color), ephemeral=True)
                return
            
            case ReactRoleMenuType.UNIQUE.value:
                roles: list[discord.Role] =  [interaction.guild.get_role(int(role)) for role in menu['roles'].keys()]
                await interaction.response.send_message(content="<a:TGK_loading:1222135771935412287> Please wait...", ephemeral=True)
                added_roles = ""
                removed_roles = ""
                for arole in roles:
                    if arole in interaction.user.roles: await interaction.user.remove_roles(arole); removed_roles += f"{arole.mention}, "
                await interaction.user.add_roles(role)
                added_roles += f"{role.mention}, "
                embed = discord.Embed(color=interaction.client.default_color)
                embed.description = f"Added Role(s): {added_roles}\nRemoved Role(s): {removed_roles}"
                await interaction.edit_original_response(embed=embed, content=None)                
            
            case _:
                await interaction.response.send_message(embed=discord.Embed(description=f"Invalid menu type", color=discord.Color.red()), ephemeral=True)
                return

class RoleMenu_Select(Select):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    async def callback(self, interaction: Interaction):

        menu: RoleMenuProfile = self.view.menu
        _roles: list[discord.Role] = []
        for role in self.values:
            role = interaction.guild.get_role(int(role))
            if role: _roles.append(role)

        match menu['type']:

            case ReactRoleMenuType.ADD_ONLY.value:
                added_roles = ""
                await interaction.response.defer(ephemeral=True, thinking=True)
                roles_to_add = []
                for role in _roles:
                    if role not in interaction.user.roles:
                        roles_to_add.append(role)
                await interaction.user.add_roles(*roles_to_add)              
                embed = discord.Embed(color=interaction.client.default_color)
                embed.add_field(name="Added Role(s)", value=added_roles, inline=False)
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            case ReactRoleMenuType.REMOVE_ONLY.value:
                removed_roles = ""
                roles_to_remove = []
                await interaction.response.defer(ephemeral=True, thinking=True)
                for role in _roles:
                    if role in interaction.user.roles:
                        roles_to_remove.append(role)
                        removed_roles += f"{role.mention}, "
                await interaction.user.remove_roles(*roles_to_remove)
                embed = discord.Embed(color=interaction.client.default_color)
                embed.add_field(name="Removed Role(s)", value=removed_roles, inline=False)
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            case ReactRoleMenuType.ADD_AND_REMOVE.value | ReactRoleMenuType.DEFAULT:
                added_roles = ""
                removed_roles = ""
                roles_to_add = []
                roles_to_remove = []
                await interaction.response.defer(ephemeral=True, thinking=True)
                for role in _roles:
                    if role in interaction.user.roles:
                        roles_to_remove.append(role)
                        removed_roles += f"{role.mention}, "
                    else:
                        roles_to_add.append(role)
                        added_roles += f"{role.mention}, "
                await interaction.user.add_roles(*roles_to_add)
                await interaction.user.remove_roles(*roles_to_remove)
                embed = discord.Embed(color=interaction.client.default_color)
                embed.add_field(name="Added Role(s)", value=added_roles, inline=False)
                embed.add_field(name="Removed Role(s)", value=removed_roles, inline=False)
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            case ReactRoleMenuType.UNIQUE.value:
                roles: list[discord.Role] =  [interaction.guild.get_role(int(role)) for role in menu['roles'].keys()]
                await interaction.response.send_message(content="<a:TGK_loading:1222135771935412287> Please wait...", ephemeral=True)
                added_roles = ""
                removed_roles = ""
                for arole in roles:
                    if arole in interaction.user.roles: await interaction.user.remove_roles(arole); removed_roles += f"{arole.mention}, "
                for role in _roles:
                    await interaction.user.add_roles(role)
                    added_roles += f"{role.mention}, "
                embed = discord.Embed(color=interaction.client.default_color)
                embed.description = f"Added Role(s): {added_roles}\nRemoved Role(s): {removed_roles}"
                await interaction.edit_original_response(embed=embed, content=None)
                return

            case _:
                await interaction.response.send_message(embed=discord.Embed(description=f"Invalid menu type", color=discord.Color.red()), ephemeral=True)
                return


class RoleMenu_Perent(View):
    def __init__(self, menu: RoleMenuProfile, guild: discord.Guild, timeout: int=None, message: discord.Message=None, labled:bool=False, _type: str="button"):
        self.menu = menu
        self.requried_roles = self.menu['req_roles']
        self.blacklisted_roles = self.menu['bl_roles']
        self.type = self.menu['type']
        self.guild = guild
        self.message = message
        self.labled = labled
        self._type = _type
        super().__init__(timeout=timeout)
        match self._type:
            case "button":
                for role in self.menu['roles'].values():
                    if self.labled is False:
                        self.add_item(
                            RoleMenu_Button(
                                style=ButtonStyle.gray,
                                emoji=role['emoji'],
                                custom_id=f"react_roles:{self.guild.id}:{self.menu['name']}:{role['role_id']}"
                            )
                        )
                    else:
                        _role = self.guild.get_role(role['role_id'])
                        if _role:
                            self.add_item(
                                Button(
                                    style=ButtonStyle.gray,
                                    label=_role.name,
                                    emoji=role['emoji'],
                                    custom_id=f"react_roles:{self.guild.id}:{self.menu['name']}:{role['role_id']}"
                                )
                            )
            case "dropdown":
                option: list[SelectOption] = []
                for role in self.menu['roles'].values():
                    _role = self.guild.get_role(role['role_id'])
                    if _role:
                        option.append(SelectOption(label=_role.name, value=_role.id, emoji=role['emoji']))

                select = RoleMenu_Select(placeholder="Tap here to modify your roles", options=option, max_values=len(option), min_values=1, custom_id=f"react_roles:{self.guild.id}:{self.menu['name']}")
                self.add_item(select)

    async def interaction_check(self, interaction: Interaction):
        user_role = [role.id for role in interaction.user.roles]
        if (set(user_role) & set(self.blacklisted_roles)):
            bl_roles = ""
            for role in self.blacklisted_roles:
                bl_roles += f"<@&{role}>, "
            await interaction.response.send_message(f"You have blacklisted roles to use this menu\n", ephemeral=True)
            return False
        
        if (set(user_role) & set(self.requried_roles)):
            req_roles = ""
            for role in self.requried_roles:
                req_roles += f"<@&{role}>, "
            await interaction.response.send_message(f"You don't have the required roles to use this menu\nRequired Roles: {req_roles}", ephemeral=True)
            return False
        
        return True

    async def on_timeout(self):
        if isinstance(self.message, discord.Message):
            for btn in self.children:
                btn.disabled = True
            try:
                await self.message.edit(view=self)
            except:
                pass
    
    async def on_error(self, interaction: Interaction, error: Exception, item: Item[Any]) -> None:
        raise error