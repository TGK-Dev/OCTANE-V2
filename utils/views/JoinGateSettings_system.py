import discord
from discord import Interaction, SelectOption
from discord.ui import View, Button, button, TextInput, Item
from .selects import Role_select, Select_General, Channel_select
from .modal import General_Modal


class JoinGateSettings_Edit(View):
    def __init__(self, interaction: Interaction, data:dict, message: discord.Message=None):
        self.interaction = interaction
        self.message = message
        self.data = data
        self.value = False
        super().__init__()
    
    def update_embed(self, data):
        embed = discord.Embed(title="Join Gate Settings", description="", color=0x2b2d31)
        embed.description += f"**Enabled:** `{data['joingate']['enabled']}`\n"
        embed.description += f"**Decancer:** `{data['joingate']['decancer'] if data['joingate']['decancer'] is not None else 'None'}`\n"
        embed.description += f"**Action:** `{data['joingate']['action'] if data['joingate']['action'] is not None else 'None'}`\n"
        embed.description += f"**Account Age:** `{str(data['joingate']['accountage']) +(' Days') if data['joingate']['accountage'] is not None else 'None'}`\n"
        embed.description += f"**Whitelist:** {','.join([f'<@{user}>' for user in data['joingate']['whitelist']]) if len(data['joingate']['whitelist']) > 0 else '`None`'}\n"
        embed.description += f"**Auto Role:** {','.join([f'<@&{role}>' for role in data['joingate']['autorole']]) if len(data['joingate']['autorole']) > 0 else '`None`'}\n"
        embed.description += f"**Log Channel:** {self.interaction.guild.get_channel(data['joingate']['logchannel']).mention if data['joingate']['logchannel'] is not None else '`None`'}\n"

        return embed

    @button(label="Toggle", style=discord.ButtonStyle.gray, custom_id="joingate_toggle", row=0)
    async def joingate_toggle(self,  interaction: discord.Interaction, button: discord.ui.Button):
        if self.data['joingate']['enabled'] == True:self.data['joingate']['enabled'] = False
        else:self.data['joingate']['enabled'] = True
        await interaction.response.edit_message(embed=self.update_embed(self.data), view=self)
    
    @button(label="Decancer", style=discord.ButtonStyle.gray, custom_id="joingate_decancer", row=0)
    async def joingate_decancer(self,  interaction: discord.Interaction, button: discord.ui.Button):
        if self.data['joingate']['decancer'] == True:self.data['joingate']['decancer'] = False
        else:self.data['joingate']['decancer'] = True
        await interaction.response.edit_message(embed=self.update_embed(self.data), view=self)

    @button(label="Action", style=discord.ButtonStyle.gray, custom_id="joingate_action", row=0)
    async def joingate_action(self,  interaction: discord.Interaction, button: discord.ui.Button):
        view = View()
        view.value = False
        options = [SelectOption(label="Kick", value="kick"), SelectOption(label="Ban", value="ban")]
        view.select = Select_General(placeholder="Please select to perform", options=options, max_values=1)
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()
        if view.value:
            self.data['joingate']['action'] = view.select.values[0]
            await interaction.message.edit(embed=self.update_embed(self.data), view=self)
            await view.select.interaction.response.edit_message(view=None, embed=discord.Embed(description=f"Join Gate action has been updated to {view.select.values[0]}"))
        else:
            await interaction.delete_original_response()

    @button(label="Account Age", style=discord.ButtonStyle.gray, custom_id="joingate_accountage", row=1)
    async def joingate_accountage(self,  interaction: discord.Interaction, button: discord.ui.Button):
        view = View()
        view.value = False
        options = [SelectOption(label="1 Day", value="1"), SelectOption(label="2 Days", value="2"), SelectOption(label="3 Days", value="3"), SelectOption(label="4 Days", value="4"), SelectOption(label="5 Days", value="5"), SelectOption(label="6 Days", value="6"), SelectOption(label="7 Days", value="7")]
        view.select = Select_General(placeholder="Please select account age", options=options, max_values=1)
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()
        if view.value:
            self.data['joingate']['accountage'] = int(view.select.values[0])
            await interaction.message.edit(embed=self.update_embed(self.data), view=self)
            await view.select.interaction.response.edit_message(view=None, embed=discord.Embed(description=f"Join Gate account age has been updated to {view.select.values[0]} Days"))
        else:
            await interaction.delete_original_response()

    @button(label="Whitelist", style=discord.ButtonStyle.gray, custom_id="joingate_whitelist", row=1)
    async def joingate_whitelist(self,  interaction: discord.Interaction, button: discord.ui.Button):
        modal = General_Modal(title="Whitelist Users Form", interaction=interaction)
        modal.qestion = TextInput(label="Whitelist Users", placeholder="Please enter user ids to whitelist", max_length=1000)
        if self.data['joingate']['whitelist'] is not None:modal.qestion.default = ','.join(self.data['joingate']['whitelist'])
        modal.add_item(modal.qestion)
        await interaction.response.send_modal(modal)
        await modal.wait()
        if modal.value:
            self.data['joingate']['whitelist']= []
            for user in modal.qestion.value.split(','):
                if int(user) not in self.data['joingate']['whitelist']:
                    self.data['joingate']['whitelist'].append(int(user))
            await modal.interaction.response.edit_message(embed=self.update_embed(self.data), view=self)
        
    @button(label="Auto Role", style=discord.ButtonStyle.gray, custom_id="joingate_autorole", row=1)
    async def joingate_autorole(self,  interaction: discord.Interaction, button: discord.ui.Button):
        view = View()
        view.value = False
        view.select = Role_select(placeholder="Please select roles to add/remove", max_values=10, min_values=1)
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()
        if view.value:
            add_roles = ""
            remove_roles = ""
            failed_roles = ""

            for role in view.select.values:
                if role == interaction.guild.default_role: failed_roles += f"{role.mention}, "; continue
                if role.position + 1 > interaction.guild.me.top_role.position: failed_roles += f"{role.mention}, "; continue
                if role.permissions.administrator or role.permissions.manage_guild or role.permissions.manage_roles or role.permissions.kick_members or role.permissions.ban_members: failed_roles += f"{role.mention}, "; continue
            
                if role.id in self.data['joingate']['autorole']:
                    self.data['joingate']['autorole'].remove(role.id)
                    remove_roles += f"{role.mention}, "
                else:
                    self.data['joingate']['autorole'].append(role.id)
                    add_roles += f"{role.mention}, "
            await view.select.interaction.response.edit_message(content=f"Added roles: {add_roles}\nRemoved roles: {remove_roles}\nFailed roles: {failed_roles}", view=None)
            await interaction.message.edit(embed=self.update_embed(self.data), view=self)
        else:
            await interaction.delete_original_response()
    
    @button(label="Log Channel", style=discord.ButtonStyle.gray, custom_id="joingate_logchannel", row=1)
    async def joingate_logchannel(self,  interaction: discord.Interaction, button: discord.ui.Button):
        view = View()
        view.value = False
        view.select = Channel_select(placeholder="Please select a channel", max_values=1, min_values=1, channel_types=[discord.ChannelType.text])
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()
        if view.value:
            self.data['joingate']['logchannel'] = view.select.values[0].id
            await interaction.message.edit(embed=self.update_embed(self.data), view=self)
            await view.select.interaction.response.edit_message(view=None, embed=discord.Embed(description=f"Join Gate log channel has been updated to {view.select.values[0].mention}"))
        else:
            await interaction.delete_original_response()
    
    @button(label="Save", style=discord.ButtonStyle.gray, custom_id="joingate_save", row=2)
    async def joingate_save(self,  interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        for button in self.children:button.disabled = True
        await interaction.message.edit(view=self)
        await interaction.response.send_message(content="Saved", ephemeral=True)
        self.stop()