import discord
import chat_exporter
import datetime
import io
from discord import Interaction, TextStyle
from discord.ui import View, Button, button, TextInput, Item
from .selects import Channel_select, Role_select, Color_Select
from .modal import Question_Modal, Panel_Description_Modal, Panel_emoji, Panel_Question, General_Modal
from .buttons import Confirm
from typing import Any
class Config_Edit(View):
    def __init__(self, user: discord.Member, data: dict, message: discord.Message=None):
        self.user = user
        self.data = data
        self.value = None
        self.message = message
        super().__init__(timeout=120)
    
    def update_embed(self, data: dict):
        embed = discord.Embed(title="Ticket Config", color=0x2b2d31, description="")
        embed.description += f"**Category:**" + (f" <#{data['category']}>" if data['category'] is not None else "`None`") + "\n"
        embed.description += f"**Channel:**" + (f" <#{data['channel']}>" if data['channel'] is not None else "`None`") + "\n"
        embed.description += f"**Logging:**" + (f" <#{data['logging']}>" if data['logging'] is not None else "`None`") + "\n"
        embed.description += f"**Transcript:**" + (f" <#{data['transcript']}>" if data['transcript'] is not None else "`None`") + "\n"
        embed.description += f"**Panel Message:**" + (f"{data['last_panel_message_id']}" if data['last_panel_message_id'] is not None else "`None`") + "\n"
        embed.description += f"**Panels:**" + (f"`{len(data['panels'])}`" if data['panels'] is not None else "`0`") + "\n"
        return embed

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("You are not the owner of this config", ephemeral=True)
            return False
        return True
    
    async def on_timeout(self) -> None:
        for button in self.children: button.disabled = True
        await self.message.edit(view=self)
    
    async def on_error(self, error: Exception, item: Item, interaction: Interaction) -> None:
        try:
            await interaction.response.send_message(f"An error occured: {error}", ephemeral=True)
        except:
            await interaction.followup.send(f"An error occured: {error}", ephemeral=True)
    
    @button(label="Category", style=discord.ButtonStyle.gray, emoji="<:category:1068484752664973324>", row=0)
    async def category(self, interaction: Interaction, button: Button):
        embed = discord.Embed(description="Select a category for the ticket system to use", color=0x2b2d31)
        view = View()
        view.value = None
        view.select = Channel_select(placeholder="Select a category", min_values=1, max_values=1, channel_types=[discord.ChannelType.category])
        view.add_item(view.select)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True, delete_after=30)
        await view.wait()
        if view.value is None:
            await interaction.delete_original_response()
        else:
            await view.select.interaction.response.edit_message(view=None, embed=discord.Embed(description="<:octane_yes:1019957051721535618> | Category set!", color=0x2b2d31))
            self.data["category"] = view.select.values[0].id
            embed = self.update_embed(self.data)
            for button in self.children: 
                if button.label == "Save": button.disabled = False
            await interaction.message.edit(embed=embed ,view=self)
    
    @button(label="Channel", style=discord.ButtonStyle.gray, emoji="<:channel:1017378607863181322>", row=0)
    async def channel(self, interaction: Interaction, button: Button):
        embed = discord.Embed(description="Select a channel for the ticket system to use", color=0x2b2d31)
        view = View()
        view.value = None
        view.select = Channel_select(placeholder="Select a channel", min_values=1, max_values=1, channel_types=[discord.ChannelType.text])
        view.add_item(view.select)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True, delete_after=30)
        await view.wait()
        if view.value is None:
            await interaction.delete_original_response()
        else:
            await view.select.interaction.response.edit_message(view=None, embed=discord.Embed(description="<:octane_yes:1019957051721535618> | Channel set!", color=0x2b2d31))
            self.data["channel"] = view.select.values[0].id
            embed = self.update_embed(self.data)
            for button in self.children: 
                if button.label == "Save": button.disabled = False
            await interaction.message.edit(embed=embed ,view=self)
    
    @button(label="Logging", style=discord.ButtonStyle.gray, emoji="<:logging:1017378971140235354>", row=1)
    async def logging(self, interaction: Interaction, button: Button):
        embed = discord.Embed(description="Select a channel for the ticket system to log to", color=0x2b2d31)
        view = View()
        view.value = None
        view.select = Channel_select(placeholder="Select a channel", min_values=1, max_values=1, channel_types=[discord.ChannelType.text])
        view.add_item(view.select)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True, delete_after=30)
        await view.wait()
        if view.value is None:
            await interaction.delete_original_response()
        else:
            await view.select.interaction.response.edit_message(view=None, embed=discord.Embed(description="<:octane_yes:1019957051721535618> | Logging channel set!", color=0x2b2d31))
            self.data["logging"] = view.select.values[0].id
            embed = self.update_embed(self.data)
            for button in self.children: 
                if button.label == "Save": button.disabled = False
            await interaction.message.edit(embed=embed ,view=self)
    
    @button(label="Transcript", style=discord.ButtonStyle.gray, emoji="<:transcript:1069193529403916338>", row=1)
    async def transcript(self, interaction: Interaction, button: Button):
        embed = discord.Embed(description="Select a channel for the ticket system to send transcripts to", color=0x2b2d31)
        view = View()
        view.value = None
        view.select = Channel_select(placeholder="Select a channel", min_values=1, max_values=1, channel_types=[discord.ChannelType.text])
        view.add_item(view.select)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True, delete_after=30)
        await view.wait()
        if view.value is None:
            await interaction.delete_original_response()
        else:
            await view.select.interaction.response.edit_message(view=None, embed=discord.Embed(description="<:octane_yes:1019957051721535618> | Transcript channel set!", color=0x2b2d31))
            self.data["transcript"] = view.select.values[0].id
            embed = self.update_embed(self.data)
            for button in self.children: 
                if button.label == "Save": button.disabled = False
            await interaction.message.edit(embed=embed ,view=self)
    
    @button(label="Save", style=discord.ButtonStyle.green, emoji="<:save:1068611610568040539>",row=2)
    async def save(self, interaction: Interaction, button: Button):
        for button in self.children: button.disabled = True
        await interaction.message.edit(view=self)
        await interaction.response.send_message("Saved!", ephemeral=True, delete_after=5)
        self.value = True
        self.stop()

    async def on_timeout(self):
        for button in self.children: button.disabled = True
        await self.message.edit(view=self)
    
    async def on_error(self, error, item, interaction):
        try:
            await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True, delete_after=5)
        except:
            await interaction.edit_original_response(content=f"An error occurred: {error}", view=self)

    async def interaction_check(self, interaction: Interaction):
        if interaction.user.id == self.user.id:
            return True
        else:
            await interaction.response.send_message("You are not allowed to use this view", ephemeral=True, delete_after=5)
            return False

class Panel_Edit(View):
    def __init__(self, user: discord.Member, data:dict, message: discord.Message=None):
        self.user = user
        self.data = data
        self.value = None
        self.message = message
        super().__init__(timeout=120)
    
    def update_embed(self, data:dict):
        embed = discord.Embed(title=f"Settings for Panel: {data['key']}", color=0x2b2d31, description="")
        embed.description += f"**Support Roles:** {', '.join([f'<@&{role}>' for role in data['support_roles']]) if len(data['support_roles']) > 0 else '`None`'}\n"
        embed.description += f"**Ping Role:**" + (f" <@&{data['ping_role']}>" if data['ping_role'] is not None else "`None`") + "\n"
        embed.description += f"**Description:**" + (f"```\n{data['description']}\n```" if data['description'] is not None else "`None`") + "\n"
        embed.description += f"**Emoji:**" + (f" {data['emoji']}" if data['emoji'] is not None else "`None`") + "\n"
        embed.description += f"**Color:**" + (f" {data['color']}" if data['color'] is not None else "`None`") + "\n"
        embed.description += f"**Modal:** " + (f"\n> Type: {data['modal']['type']}\n") + (f"```\n{data['modal']['question']}\n```" if data['modal']['question'] is not None else "`None`") + "\n"
        return embed

    async def on_timeout(self):
        for button in self.children: button.disabled = True
        await self.message.edit(view=self)
    
    async def on_error(self, error, item, interaction):
        try:
            await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)
        except:
            await interaction.followup.send(f"An error occurred: {error}", ephemeral=True)
    
    async def interaction_check(self, interaction: Interaction):
        if interaction.user.id == self.user.id:
            return True
        else:
            await interaction.response.send_message("You are not allowed to use this view", ephemeral=True)
            return False
    

    
    @button(label="Support Roles", style=discord.ButtonStyle.gray, emoji="<:managers:1017379642862215189>", row=0)
    async def support_roles(self, interaction: Interaction, button: Button):
        view = View()
        view.value = None
        view.select = Role_select(placeholder="Please select support roles", min_values=1, max_values=10)
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True, delete_after=30)
        await view.wait()
        if view.value is None:
            await interaction.delete_original_response()
        else:
            await view.select.interaction.response.edit_message(view=None, embed=discord.Embed(description="<:octane_yes:1019957051721535618> | Support roles set!", color=0x2b2d31))
            await interaction.delete_original_response()
            self.data["support_roles"] = [role.id for role in view.select.values]
            embed = self.update_embed(self.data)
            for button in self.children: 
                if button.label == "Save": button.disabled = False
            await interaction.message.edit(embed=embed ,view=self)
    
    @button(label="Ping Role", style=discord.ButtonStyle.gray, emoji="<:role_mention:1063755251632582656>", row=0)
    async def ping_role(self, interaction: Interaction, button: Button):
        view = View()
        view.value = None
        view.select = Role_select(placeholder="Please select a role to ping", min_values=1, max_values=1)
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True, delete_after=30)
        await view.wait()
        if view.value is None:
            await interaction.delete_original_response()
        else:
            await view.select.interaction.response.edit_message(view=None, embed=discord.Embed(description="<:octane_yes:1019957051721535618> | Ping role set!", color=0x2b2d31))
            await interaction.delete_original_response()
            self.data["ping_role"] = view.select.values[0].id
            embed = self.update_embed(self.data)
            for button in self.children: 
                if button.label == "Save":
                    button.disabled = False
            await interaction.message.edit(embed=embed ,view=self)

    @button(label="Description", style=discord.ButtonStyle.gray, emoji="<:description:1063755251632582656>", row=1)
    async def description(self, interaction: Interaction, button: Button):
        modal = Panel_Description_Modal(self.data)
        modal.qestion = TextInput(label="Set the description for the panel", max_length=500, style=TextStyle.long)
        if self.data["description"] is not None:modal.qestion.default = self.data["description"]
        else: modal.qestion.placeholder = "Enter a description"
        modal.add_item(modal.qestion)
        await interaction.response.send_modal(modal)
        await modal.wait()

        if modal.value:
            self.data["description"] = modal.qestion.value
            embed = self.update_embed(self.data)
            for button in self.children: 
                if button.label == "Save": button.disabled = False
            await modal.interaction.response.edit_message(view=self, embed=embed)
            modal.stop()

    @button(label="Emoji", style=discord.ButtonStyle.gray, emoji="<:embed:1017379990289002536>", row=1)
    async def emoji(self, interaction: Interaction, button: Button):
        modal = Panel_emoji(self.data)
        modal.qestion= TextInput(label="Set the emoji for the panel", max_length=300)
        if self.data["emoji"] is not None:modal.qestion.default = self.data["emoji"]
        else: modal.qestion.placeholder = "Enter an emoji"
        modal.add_item(modal.qestion)
        await interaction.response.send_modal(modal)
        await modal.wait()

        if modal.value:
            self.data["emoji"] = modal.qestion.value
            embed = self.update_embed(self.data)
            for button in self.children: 
                if button.label == "Save": button.disabled = False
            await modal.interaction.response.edit_message(view=self, embed=embed)
            modal.stop()

    @button(label="Color", style=discord.ButtonStyle.gray, emoji="<:color:1017379990289002536>", row=1)
    async def color(self, interaction: Interaction, button: Button):
        view = View()
        view.value = None
        view.select = Color_Select()
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True, delete_after=30)
        await view.wait()
        if view.value:
            self.data["color"] = view.select.values[0]
            await view.select.interaction.response.edit_message(view=None, embed=discord.Embed(description=f"<:octane_yes:1019957051721535618> | Color set to {self.data['color']}!", color=0x2b2d31))
            await interaction.delete_original_response()            
            embed = self.update_embed(self.data)
            for button in self.children: 
                if button.label == "Save": button.disabled = False
            await interaction.message.edit(embed=embed ,view=self)
    
    @button(label="Questionnaire", style=discord.ButtonStyle.gray, emoji="<:StageIconRequests:1005075865564106812>", row=2)
    async def questionnaire(self, interaction: Interaction, button: Button):
        modal = Question_Modal(self.data)
        modal.qestion_type = TextInput(label="Set type of asnwer", max_length=20)

        if self.data["modal"]["type"] is not None:modal.qestion_type.placeholder = "Avable types: (long,short)"
        else: modal.qestion_type.default = "short"
        modal.qestion = TextInput(label="Set the question for the panel", max_length=300)
        if self.data["modal"]["question"] is not None:modal.qestion.default = self.data["modal"]["question"]
        else: modal.qestion.placeholder = "Enter a question"

        modal.add_item(modal.qestion_type)
        modal.add_item(modal.qestion)
        await interaction.response.send_modal(modal)
        await modal.wait()

        if modal.value:
            embed = self.update_embed(self.data)
            self.data["modal"]["type"] = modal.qestion_type.value
            self.data["modal"]["question"] = modal.qestion.value
            for button in self.children: 
                if button.label == "Save": button.disabled = False
            await modal.interaction.response.edit_message(view=self, embed=embed)

    @button(label="Save", style=discord.ButtonStyle.green, emoji="<:save:1068611610568040539>", disabled=True, row=3)
    async def save(self, interaction: Interaction, button: Button):
        for button in self.children: button.disabled = True
        await interaction.response.send_message("Panel saved!", ephemeral=True, delete_after=5)
        await interaction.message.edit(view=None)
        self.value = True
        self.stop()
    
    @button(label="Reset", style=discord.ButtonStyle.red, emoji="<:reload:1068890244226764943>", row=3)
    async def reset(self, interaction: Interaction, button: Button):
        for button in self.children: 
            if button.label == "Save": button.disabled = True
        self.data = {'key': self.data['key'], 'support_roles': [], "ping_role": None, 'created_by': interaction.user.id, 'description': None, 'emoji': None, 'color': None, 'modal': {'type': 'short', 'question': "Please describe your issue"}}
        embed = self.update_embed(self.data)
        await interaction.response.send_message("Panel reset!", ephemeral=True, delete_after=5)
        await interaction.message.edit(embed=embed ,view=self)

class ParterShip_Button(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    async def callback(self, interaction: Interaction):
        ticket_config = await interaction.client.tickets.config.find(interaction.guild.id)
        if ticket_config is None: await interaction.response.send_message("No ticket config found", ephemeral=True, delete_after=5)
        try:panel = ticket_config["panels"][self.label]
        except KeyError: return await interaction.response.send_message("Invalid panel", ephemeral=True, delete_after=5)

        if "partnership" not in panel["key"].lower(): return await interaction.response.send_message("Invalid panel", ephemeral=True, delete_after=5)

        modal = General_Modal(title="Partnership form for "+interaction.guild.name, interaction=interaction)
        modal.server_name = TextInput(label="Server name", max_length=100, placeholder="Enter your server name", style=TextStyle.short, required=True)
        modal.partnership_type = TextInput(label="Partnership type", max_length=100, placeholder="Enter your partnership type [Normal, Heist, Event]", style=TextStyle.short, required=True)
        modal.server_link = TextInput(label="Server link", max_length=100, placeholder="Enter your server valid invite link", style=TextStyle.short, required=True)

        modal.add_item(modal.server_name)
        modal.add_item(modal.partnership_type)
        modal.add_item(modal.server_link)

        await interaction.response.send_modal(modal)
        await modal.wait()
        if modal.value == False:
            return
        await modal.interaction.response.send_message("Please wait while we create your ticket", ephemeral=True)
        invite = modal.server_link.value.split("/")[-1]
        try: invite = await interaction.client.fetch_invite(invite)
        except discord.errors.NotFound: 
            embed = discord.Embed(description="Invite link you provided is invalid or expired", color=interaction.client.default_color)
            return await modal.interaction.edit_original_response(embed=embed, content=None)

        Content = f"**Server Name:** {invite.guild.name}\n**Server Aproximate Members:** {invite.approximate_member_count}\n**Server ID:** `{invite.guild.id}`\n**Server Invite:** {invite}"

        over_write = {
                interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.guild.me: discord.PermissionOverwrite(view_channel=True, manage_channels=True, manage_roles=True, manage_messages=True, manage_webhooks=True, manage_permissions=True),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True, embed_links=True, add_reactions=True)
        }

        for i in panel['support_roles']:
                role = interaction.guild.get_role(i)
                if role is not None: over_write[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True, embed_links=True, add_reactions=True)
        
        ticket = await interaction.guild.create_text_channel(f"ticket-{interaction.user.display_name}", overwrites=over_write, category=interaction.guild.get_channel(ticket_config["category"]), topic=f"Ticket for {interaction.user.mention} ({interaction.user.id})")
        ticket_embed = discord.Embed(title=f"Ticket for {interaction.user.display_name}", description="",color=0x2b2d31)
        ticket_embed.description += "Kindly wait patiently. A staff member will assist you shortly.If you're looking to approach a specific staff member, ping the member once. Do not spam ping any member or role."
        ticket_embed.set_footer(text=f"Developers: JAY#0138 & utki007#0007")
        ticket_embed.set_thumbnail(url=interaction.guild.icon.url)
        content = f"{interaction.user.mention}"
        if panel['ping_role'] is not None: content += f"|<@&{panel['ping_role']}>"
        await ticket.send(embed=ticket_embed, content=content, view=Ticket_controll())
        msg = await ticket.send(content=Content)
        await msg.pin()
        
        ticket_data = {
            "_id": ticket.id,
            "user": interaction.user.id,
            "panel": panel["key"],
            "added_roles": [],
            "status": "open",
            "added_users": [],
            "log_message_id": None,
        }
        if ticket_config['logging'] is not None:
            log_embed = discord.Embed(description="", color=0x2b2d31)
            log_embed.description += f"**Ticket created by {interaction.user.mention}**\n"
            log_embed.description += f"**Channel:** {ticket.mention}({ticket.name}|{ticket.id})\n"
            log_embed.description += f"**Panel:** {panel['key']}\n"
            log_embed.description += f"**Ticket ID:** {ticket.id}\n"
            log_embed.set_footer(text=f"Developers: JAY#0138 & utki007#0007")
            log_embed.set_thumbnail(url=interaction.guild.icon.url)
            log_channel = interaction.guild.get_channel(ticket_config['logging'])
            if log_channel is not None: 
                message = await log_channel.send(embed=log_embed)
                ticket_data["log_message_id"] = message.id
        
        await interaction.client.tickets.tickets.insert(ticket_data)
        embed = discord.Embed(description=f"Ticket created at {ticket.mention}", color=interaction.client.default_color)
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Jump to ticket", url=ticket.jump_url, style=discord.ButtonStyle.url))
        await modal.interaction.edit_original_response(embed=embed, view=view)


class Panel_Button(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def callback(self, interaction: Interaction):
        
        ticket_config = await interaction.client.tickets.config.find(interaction.guild.id)
        if ticket_config is None: await interaction.response.send_message("No ticket config found", ephemeral=True, delete_after=5)
        try:panel = ticket_config["panels"][self.label]
        except KeyError: return await interaction.response.send_message("Invalid panel", ephemeral=True, delete_after=5)

        modal = Panel_Question(title=f"{panel['key']}'s form")
        modal.answer = TextInput(label=panel["modal"]["question"], max_length=500, placeholder="Enter your quries here", style=TextStyle.long if panel["modal"]["type"] == "long" else TextStyle.short)
        modal.add_item(modal.answer)
        await interaction.response.send_modal(modal)
        await modal.wait()

        if modal.value:
            await modal.interaction.response.send_message(f"Please wait while we create your ticket", ephemeral=True)

            over_write = {
                interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.guild.me: discord.PermissionOverwrite(view_channel=True, manage_channels=True, manage_roles=True, manage_messages=True, manage_webhooks=True, manage_permissions=True),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True, embed_links=True, add_reactions=True)
            }
            for i in panel['support_roles']:
                role = interaction.guild.get_role(i)
                if role is not None: over_write[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True, embed_links=True, add_reactions=True)

            ticket = await interaction.guild.create_text_channel(f"ticket-{interaction.user.display_name}", overwrites=over_write, category=interaction.guild.get_channel(ticket_config["category"]), topic=f"Ticket for {interaction.user.mention} ({interaction.user.id})")
            ticket_embed = discord.Embed(title=f"Ticket for {interaction.user.display_name}", description="",color=0x2b2d31)
            ticket_embed.description += "Kindly wait patiently. A staff member will assist you shortly.If you're looking to approach a specific staff member, ping the member once. Do not spam ping any member or role."
            ticket_embed.set_footer(text=f"Developers: JAY#0138 & utki007#0007")
            ticket_embed.set_thumbnail(url=interaction.guild.icon.url)
            ticket_embed.add_field(name=modal.answer.label, value=modal.answer.value, inline=False)
            content = f"{interaction.user.mention}"
            if panel['ping_role'] is not None: content += f"|<@&{panel['ping_role']}>"
            msg = await ticket.send(embed=ticket_embed, content=content, view=Ticket_controll())
            await msg.pin()
            ticket_data = {
                "_id": ticket.id,
                "user": interaction.user.id,
                "panel": panel["key"],
                "added_roles": [],
                "status": "open",
                "added_users": [],
                "log_message_id": None,
            }
            if ticket_config['logging'] is not None:
                log_embed = discord.Embed(description="", color=0x2b2d31)
                log_embed.description += f"**Ticket created by {interaction.user.mention}**\n"
                log_embed.description += f"**Channel:** {ticket.mention}({ticket.name}|{ticket.id})\n"
                log_embed.description += f"**Panel:** {panel['key']}\n"
                log_embed.description += f"**Ticket ID:** {ticket.id}\n"
                log_embed.set_footer(text=f"Developers: JAY#0138 & utki007#0007")
                log_embed.set_thumbnail(url=interaction.guild.icon.url)
                log_channel = interaction.guild.get_channel(ticket_config['logging'])
                if log_channel is not None: 
                    message = await log_channel.send(embed=log_embed)
                    ticket_data["log_message_id"] = message.id
            
            await interaction.client.tickets.tickets.insert(ticket_data)
            await modal.interaction.edit_original_response(content=f"Ticket created! {ticket.mention}", view=None)

class Panel_View(View):
    def __init__(self):     
        super().__init__(timeout=None)
    
    async def on_error(self, interaction: Interaction, error: Exception, item: Item[Any], /) -> None:
        try:
            await interaction.response.send_message(f"An error occured: {error}", ephemeral=True)
        except:
            await interaction.followup.send(content=f"An error occured: {error}", ephemeral=True)
    

class Ticket_controll(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    async def on_error(self, interaction: Interaction, error: Exception, item: Item[Any], /) -> None:
        try:
            await interaction.response.send_message(f"An error occured: {error}", ephemeral=True)
        except:
            await interaction.followup.send(content=f"An error occured: {error}", ephemeral=True)
    
    async def log_embed(self, log_chanenl: discord.TextChannel, action: str, ticket:discord.TextChannel, user: discord.Member) -> discord.Message:
        embed = discord.Embed(description="", color=0x2b2d31)
        embed.set_author(name=f"Ticket {action}")
        embed.description += f"**Ticket:** {ticket.mention}({ticket.name}|{ticket.id})\n"
        embed.description += f"**User:** {user.mention}({user.name}|{user.id})\n"
        embed.set_footer(text=f"Developers: JAY#0138 & utki007#0007")
        
        return await log_chanenl.send(embed=embed)
    
    @button(custom_id="ticket:open", label="Open", style=discord.ButtonStyle.green, emoji="🔓")
    async def open(self, interaction: Interaction, button: Button):
        ticket_data = await interaction.client.tickets.tickets.find(interaction.channel.id)
        if ticket_data is None: return await interaction.response.send_message("No ticket found", ephemeral=True, delete_after=5)
        if ticket_data["status"] == "open": return await interaction.response.send_message("Ticket is already open", ephemeral=True, delete_after=5)

        embed = discord.Embed(description="<a:loading:998834454292344842> | Opening ticket...", color=0x2b2d31)
        await interaction.response.send_message(embed=embed, ephemeral=False)
        overwrite = discord.PermissionOverwrite(view_channel=True)
        for i in ticket_data["added_roles"]: await interaction.channel.set_permissions(interaction.guild.get_role(i), overwrite=overwrite)
        for i in ticket_data["added_users"]: 
            user = interaction.guild.get_member(i)
            if user is not None: await interaction.channel.set_permissions(user, overwrite=overwrite)
            else: ticket_data["added_users"].remove(i)
        ticket_owner = interaction.guild.get_member(ticket_data["user"])
        if ticket_owner is not None: await interaction.channel.set_permissions(ticket_owner, overwrite=overwrite)
        else: return await interaction.edit_original_response(embed=discord.Embed(description="Ticket owner not found/left the server", color=0x2b2d31))
        
        ticket_data["status"] = "open"
        await interaction.client.tickets.tickets.update(ticket_data)

        embed.description = "<:dynosuccess:1000349098240647188> | Ticket opened!"
        await interaction.edit_original_response(embed=embed)
        ticket_config = await interaction.client.tickets.config.find(interaction.guild.id)
        if ticket_config['logging'] is not None:
            log_channel = interaction.guild.get_channel(ticket_config['logging'])
            if log_channel is not None: await self.log_embed(log_channel, "opened", interaction.channel, interaction.user)
    
    @button(custom_id="ticket:close", label="Close", style=discord.ButtonStyle.red, emoji="🔒")
    async def close(self, interaction: Interaction, button: Button):
        ticket_data = await interaction.client.tickets.tickets.find(interaction.channel.id)
        if ticket_data is None: return await interaction.response.send_message("No ticket found", ephemeral=True, delete_after=5)
        if ticket_data["status"] == "closed": return await interaction.response.send_message("Ticket is already closed", ephemeral=True, delete_after=5)

        embed = discord.Embed(description="<a:loading:998834454292344842> | Closing ticket...", color=0x2b2d31)
        await interaction.response.send_message(embed=embed, ephemeral=False)
        overwrite = discord.PermissionOverwrite(view_channel=False)
        for i in ticket_data["added_roles"]: await interaction.channel.set_permissions(interaction.guild.get_role(i), overwrite=overwrite)
        for i in ticket_data["added_users"]: 
            user = interaction.guild.get_member(i)
            if user is not None: await interaction.channel.set_permissions(user, overwrite=overwrite)
            else: ticket_data["added_users"].remove(i)
        ticket_data["status"] = "closed"
        await interaction.client.tickets.tickets.update(ticket_data)
        ticket_owner = interaction.guild.get_member(ticket_data["user"])
        if ticket_owner is not None: await interaction.channel.set_permissions(ticket_owner, overwrite=overwrite)
        else: return await interaction.edit_original_response(embed=discord.Embed(description="Ticket owner not found/left the server", color=0x2b2d31))

        embed.description = "<:dynosuccess:1000349098240647188> | Ticket closed!"
        await interaction.edit_original_response(embed=embed)
        ticket_config = await interaction.client.tickets.config.find(interaction.guild.id)
        if ticket_config['logging'] is not None:
            log_channel = interaction.guild.get_channel(ticket_config['logging'])
            if log_channel is not None: await self.log_embed(log_channel, "closed", interaction.channel, interaction.user)
    
    @button(custom_id="ticket:delete", label="Delete", style=discord.ButtonStyle.red, emoji="🗑️")
    async def delete(self, interaction: Interaction, button: Button):
        ticket_data = await interaction.client.tickets.tickets.find(interaction.channel.id)
        if ticket_data is None: return await interaction.response.send_message("No ticket found", ephemeral=True, delete_after=5)
        timestemp = datetime.datetime.now() + datetime.timedelta(seconds=20)
        embed = discord.Embed(description=f"Deleting ticket in <t:{round(timestemp.timestamp())}:R>, use the button below to cancel", color=0x2b2d31)
        
        view = Confirm(interaction.user, 20)
        
        view.children[0].label = "Cancel"
        view.children.pop(1)
        await interaction.response.send_message(embed=embed, ephemeral=False, view=view)
        view.message = await interaction.original_response()
        await view.wait()

        if view.value == True:  return await view.interaction.response.edit_message(embed=discord.Embed(description="Command cancelled", color=0x2b2d31), view=None)
        else:
            for button in view.children: button.disabled = True
            await interaction.edit_original_response(embed=discord.Embed(description="<a:loading:998834454292344842> | Saving ticket...", color=0x2b2d31), view=view)

            ticket_config = await interaction.client.tickets.config.find(interaction.guild.id)
            if ticket_config['logging'] is not None: 
                log_channel = interaction.guild.get_channel(ticket_config['logging'])
                if log_channel is not None: await self.log_embed(log_channel, "deleted", interaction.channel, interaction.user)
            
            if ticket_config['transcript'] is not None:
                transcript_channel = interaction.guild.get_channel(ticket_config['transcript'])
                messages= [messages async for messages in interaction.channel.history(limit=None)]
                transcript = await chat_exporter.raw_export(channel=interaction.channel, messages=messages, tz_info="Asia/Kolkata", guild=interaction.guild, bot=interaction.client, support_dev=True, fancy_times=True)
                transcript = discord.File(io.BytesIO(transcript.encode()), filename=f"transcript-{interaction.channel.id}.html")

                transcript_message = await transcript_channel.send(file=transcript, content=f"**Channel:** {interaction.channel.name}\n**User:** <@{ticket_data['user']}>(`{ticket_data['user']}`)")
                link_view = discord.ui.View()
                link_view.add_item(discord.ui.Button(label="View Transcript", url=f"https://mahto.id/chat-exporter?url={transcript_message.attachments[0].url}"))
                await transcript_message.edit(view=link_view)
                try:
                    log_message = await log_channel.fetch_message(ticket_data["log_message_id"])
                    embed = log_message.embeds[0]
                    embed.add_field(name="Transcript", value=f"[View Transcript]({transcript_message.attachments[0].url})")
                    await log_message.edit(embed=embed, view=link_view)
                except discord.NotFound: 
                    pass

            await interaction.channel.delete()
            await interaction.client.tickets.tickets.delete(interaction.channel.id)