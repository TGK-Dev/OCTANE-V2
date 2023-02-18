import discord
from discord import Interaction, SelectOption
from discord.ui import View, Button, button, TextInput, Item
from .selects import Role_select, Select_General
from .modal import General_Modal


class ReactionRoleMenu(View):
    def __init__(self, data:dict, interaction: Interaction,message: discord.Message=None):
        self.data = data
        self.message = message
        self.interaction = interaction
        self.value= False
        super().__init__(timeout=180)
    
    def update_embed(self, data:dict):
        embed = discord.Embed(title="Setting up reaction role menu", description="", color=0x2b2d31)
        embed.description += f"**Name:** {data['name']}\n"
        embed.description += f"**Display Name:** {data['display_name'] if data['display_name'] else '`None`'}\n"
        embed.description += f"**Roles:** {','.join([f'<@&{role}>' for role in data['roles']]) if data['roles'] else '`None`'}\n"
        embed.description += f"**Required Roles:** {','.join([f'<@&{role}>' for role in data['required_roles']]) if data['required_roles'] else '`None`'}\n"
        type = '`Add & Remove`' if data['type'] == 'add_remove' else '`Add Only`' if data['type'] == 'add_only' else '`Remove Only`' if data['type'] == 'remove_only' else '`None`'
        embed.description += f"**Type:** {type}\n"
        return embed

    async def on_timeout(self):
        for child in self.children:child.disabled = True
        await self.message.edit(view=self)
    
    async def interaction_check(self, interaction: Interaction, /) -> bool:
        if interaction.user.id == self.interaction.user.id:
            return True
        else:
            await interaction.response.send_message("You are not the author of this message", ephemeral=True)
            return False
    
    async def on_error(self, error: Exception, item: Item, interaction: Interaction) -> None:
        await interaction.response.send_message("An error occured", ephemeral=True)
        raise error
    
    @button(label="Add Roles", style=discord.ButtonStyle.gray, emoji="<:role_mention:1063755251632582656>", row=0)
    async def add_roles(self,interaction: Interaction,button: Button):
        view = discord.ui.View()
        view.value = None
        view.select = Role_select(placeholder="Select roles you want to add to the menu", min_values=1, max_values=9)
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()
        if view.value:
            for role in view.select.values[::-1]:
                if role.id not in self.data["roles"]:
                    if role.position >= interaction.guild.me.top_role.position: return await view.select.interaction.response.edit_message(content=f"I can't add {role.mention} to the reaction role menu because it's higher than my highest role", view=None)
                    if role.managed: return await view.select.interaction.response.edit_message(content=f"I can't add {role.mention} to the reaction role menu because it's managed", view=None)
                    if role.is_default(): return await view.select.interaction.response.edit_message(content=f"I can't add {role.mention} to the reaction role menu because it's the default role", view=None)
                    if role.permissions.administrator or role.permissions.manage_guild or role.permissions.manage_roles or role.permissions.kick_members or role.permissions.ban_members: return await view.select.interaction.response.edit_message(content=f"I can't add {role.mention} to the reaction role menu because it has administrator or manage guild or manage roles or kick members or ban members permissions", view=None)
                    self.data["roles"].append(role.id)
            embed = self.update_embed(self.data)
            await view.select.interaction.response.edit_message(embed=discord.Embed(description="Roles added to the reaction role menu", color=0x2b2d31), view=None)
            await interaction.message.edit(embed=embed, view=self)
        else:
            await interaction.delete_original_response()
    
    @button(label="Remove Roles", style=discord.ButtonStyle.gray, emoji="<:role_mention:1063755251632582656>", row=0)
    async def remove_roles(self,interaction: Interaction,button: Button):
        view = discord.ui.View()
        view.value = None
        roles = [interaction.guild.get_role(role) for role in self.data["roles"]]
        options = [SelectOption(label=role.name, value=role.id, emoji="<:role_mention:1063755251632582656>") for role in roles]
        view.select = Select_General(placeholder="Select role you want to remove from the menu", options=options, min_values=1, max_values=len(roles))
        view.add_item(view.select)
        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()
        if view.value:
            for role in view.select.values:
                role_id = int(role)
                if role_id in self.data["roles"]:
                    self.data["roles"].remove(role_id)
            embed = self.update_embed(self.data)
            await view.select.interaction.response.edit_message(embed=discord.Embed(description=f"{','.join([f'<@&{role}>' for role in view.select.values])} removed from the reaction role menu", color=0x2b2d31), view=None)
            await interaction.message.edit(embed=embed, view=self)

    @button(label="Set Required Roles", style=discord.ButtonStyle.gray, emoji="<:role_mention:1063755251632582656>", row=0)
    async def set_required_roles(self,interaction: Interaction,button: Button):
        view = discord.ui.View()
        view.value = None
        view.select = Role_select(placeholder="Select roles", min_values=1, max_values=10)
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()
        if view.value:
            self.data["required_roles"] = [role.id for role in view.select.values]
            embed = self.update_embed(self.data)
            await view.select.interaction.response.edit_message(embed=discord.Embed(description="Required roles set for the reaction role menu", color=0x2b2d31), view=None)
            await interaction.message.edit(embed=embed, view=self)
        else:
            await interaction.delete_original_response()
    
    @button(label="Display Name", style=discord.ButtonStyle.gray, emoji="<:octane_dispay_name:1071702273832538122>", row=1)
    async def display_name(self,interaction: Interaction,button: Button):
        modal = General_Modal(title=f"{self.data['name']}'s Display Name Modal", interaction=interaction)
        modal.question = TextInput(label="Enter Display Name", placeholder="Enter Display Name", min_length=1, max_length=100)
        if self.data["display_name"]: modal.question.default = self.data["display_name"]
        modal.add_item(modal.question)
        await interaction.response.send_modal(modal)
        await modal.wait()
        if modal.value:
            embed = self.update_embed(self.data)
            self.data["display_name"] = modal.question.value
            await modal.interaction.response.edit_message(embed=embed, view=self)

    @button(label="Change Type", style=discord.ButtonStyle.gray, emoji="<:octane_rr_type:1071537084495564871>", row=1)
    async def change_type(self,interaction: Interaction,button: Button):
        view = discord.ui.View()
        view.value = None
        view.select = Select_General(interaction=interaction, options=[SelectOption(label="Add & Remove", value="add_remove", description="User can Add or Remove role from there self",default=True), SelectOption(label="Only Add", value="only_add", description="Only Allow users to add roles"), SelectOption(label="Only Remove", value="only_remove", description="Allow user to only remove role")], placeholder="Please select type of reaction role menu")
        view.add_item(view.select)
        
        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()
        if view.value:
            self.data["type"] = view.select.values[0]
            embed = self.update_embed(self.data)
            await view.select.interaction.response.edit_message(embed=discord.Embed(description="Type changed", color=0x2b2d31), view=None)
            await interaction.message.edit(embed=embed, view=self)
        else:
            await interaction.delete_original_response()

    @button(label="Save", style=discord.ButtonStyle.green, emoji="<:ace_downvote1:1004651437860589598>", row=2)
    async def save(self,interaction: Interaction,button: Button):
        for button in self.children:
            button.disabled = True
        button.label = "Saved"
        await interaction.response.send_message(embed=discord.Embed(description="Menu saved", color=0x2b2d31), ephemeral=True, delete_after=5)
        await interaction.message.edit(view=self)
        self.value = True
        self.stop()

class RoleMenu_Button(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    async def callback(self, interaction: Interaction):
        if self.view.required_roles != None:
            user_roles = [role.id for role in interaction.user.roles]
            if not (set(user_roles) & set(self.view.required_roles)):
                await interaction.response.send_message(embed=discord.Embed(description=f"You don't have the required roles to use this menu\n> Required Roles: {', '.join([f'<@&{role}>' for role in self.view.required_roles])}", color=0x2b2d31), ephemeral=True)
                return
        button_id = self.custom_id.split(":")[::-1]
        role = interaction.guild.get_role(int(button_id[0]))
        if self.view.menu_type == "add_remove":
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role)
                await interaction.response.send_message(embed=discord.Embed(description=f"Removed role {role.mention}", color=0x2b2d31), ephemeral=True)
            else:
                await interaction.user.add_roles(role)
                await interaction.response.send_message(embed=discord.Embed(description=f"Added role {role.mention}", color=0x2b2d31), ephemeral=True)
        elif self.view.menu_type == "only_add":
            if role in interaction.user.roles:
                await interaction.response.send_message(embed=discord.Embed(description=f"You already have the role {role.mention}", color=0x2b2d31), ephemeral=True)
            else:
                await interaction.user.add_roles(role)
                await interaction.response.send_message(embed=discord.Embed(description=f"Added role {role.mention}", color=0x2b2d31), ephemeral=True)
        elif self.view.menu_type == "only_remove":
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role)
                await interaction.response.send_message(embed=discord.Embed(description=f"Removed role {role.mention}", color=0x2b2d31), ephemeral=True)
            else:
                await interaction.response.send_message(embed=discord.Embed(description=f"You don't have the role {role.mention}", color=0x2b2d31), ephemeral=True)        
        else:
            await interaction.response.send_message(embed=discord.Embed(description=f"Invalid menu type", color=0x2b2d31), ephemeral=True)

class Reaction_Role_View(View):
    def __init__(self, guild_config: dict, guild: discord.Guild):
        self.guild_config = guild_config
        self.menu_type = guild_config["type"]
        self.required_roles = guild_config["required_roles"] if len(guild_config["required_roles"]) > 0 else None
        self._id = f"{guild.id}:menu:{guild_config['name']}"
        super().__init__(timeout=None)
        for role in guild_config["roles"]:
            role = guild.get_role(role)
            button = RoleMenu_Button(label=role.name, style=discord.ButtonStyle.blurple, custom_id=f"reaction_role:{guild_config['name']}:id:{role.id}")
            self.add_item(button)        
    
    # async def on_error(self, interaction: Interaction, error: Exception, item: Item[Any], /) -> None:
    #     await interaction.response.send_message(embed=discord.Embed(description=f"Error: {error}", color=0x2b2d31), ephemeral=True)

