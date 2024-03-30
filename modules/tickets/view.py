import datetime
import io
import discord
import traceback
from discord import Interaction, SelectOption, app_commands
from discord.ui import View, Button, button, TextInput, Item, Select, select
import chat_exporter
import urllib
from utils.views.selects import Role_select, Select_General, Channel_select
from utils.views.modal import General_Modal
from utils.views.buttons import Confirm
from utils.paginator import Paginator
from utils.embed import get_formated_embed, get_formated_field
from .db import TicketConfig, Panel, Qestion, Ticket
from typing import Dict, List

class TicketConfig_View(View):
    def __init__(self, user:discord.Member, data: TicketConfig, message: discord.Message=None):
        self.user = user
        self.data = data 
        self.message = message
        super().__init__(timeout=600)
    
    async def interaction_check(self, interaction: Interaction):
        if interaction.user.id == self.user.id:
            return True
        else:
            await interaction.response.send_message("You are not the owner of this perk", ephemeral=True)
            return False
    
    async def on_timeout(self):
        for child in self.children:child.disabled = True; await self.message.edit(view=self)
    
    async def on_error(self, interaction: Interaction, error: Exception, item: Item):
        try:
            await interaction.response.send_message(embed=discord.Embed(description=f"```py\n{traceback.format_exception(type(error), error, error.__traceback__, 4)}\n```", color=discord.Color.red()), ephemeral=True)
        except :
            await interaction.followup.send(embed=discord.Embed(description=f"```py\n{traceback.format_exception(type(error), error, error.__traceback__, 4)}\n```", color=discord.Color.red()), ephemeral=True)
        
    
    @button(label='Admin Role', style=discord.ButtonStyle.gray, emoji='<:tgk_role:1073908306713780284>')
    async def _admin_role_select(self, interaction: Interaction, button: Button):
        view = View()
        view.value = False
        view.select = Role_select(placeholder='Select the role you want to add/remove', min_values=1, max_values=10)
        view.add_item(view.select)
        await interaction.response.send_message(view=view, ephemeral=True, delete_after=30)
        await view.wait()

        if not view.value:
            await interaction.delete_original_response()
            return
        
        updates = {'added_roles': [], 'removed_roles': []}
        for role in view.select.values:
            if role.id in self.data['admin_roles']:
                updates['removed_roles'].append(role.mention)
                self.data['admin_roles'].remove(role.id)
            else:
                updates['added_roles'].append(role.mention)
                self.data['admin_roles'].append(role.id)
        await view.select.interaction.response.edit_message(content=f"Updated the admin roles\n\nAdded Roles: {', '.join(updates['added_roles'])}\nRemoved Roles: {', '.join(updates['removed_roles'])}", view=None, delete_after=10)
        await interaction.client.tickets.update_config(_id=self.data['_id'], data=self.data)
        await self.message.edit(embed=await interaction.client.tickets.get_config_embed(data=self.data))

    @button(label="Channels", style=discord.ButtonStyle.gray, emoji='<:tgk_channel:1073908465405268029>')
    async def _channel_select(self, interaction: Interaction, button: Button):
        view = Channel_Config()
        await interaction.response.send_message(view=view, ephemeral=True)

        await view.wait()
        if view.value is False or view.value is False:
            await interaction.delete_original_response()
            return
        
        keys = ['default_category', 'default_channel', 'log_channel', 'transcript_channel', 'nameing_scheme']
        for key in keys:
            if view.data.get(key) is not None:
                self.data[key] = view.data[key].id

        await interaction.client.tickets.update_config(_id=self.data['_id'], data=self.data)
        await self.message.edit(embed=await interaction.client.tickets.get_config_embed(data=self.data))                                              

    @button(label="Panels", style=discord.ButtonStyle.gray, emoji='<:tgk_category:1076602579846447184>')
    async def _panel_select(self, interaction: Interaction, button: Button):
        view = View()
        view.value = False
        view.select = Select_General(
            interaction=interaction, placeholder="Select the action you want to perform", options=[
                SelectOption(label="Create Panel", value="create", description="Create a new ticket panel", emoji="<:tgk_add:1073902485959352362>"),
                SelectOption(label="Edit Panel", value="edit", description="Edit a ticket panel", emoji="<:tgk_edit:1073902428224757850>"),
                SelectOption(label="Delete Panel", value="delete",  description="Delete a ticket panel", emoji="<:tgk_delete:1113517803203461222>"),
            ]
        )
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True)

        await view.wait()
        if view.value is False or view.value is False:
            await interaction.delete_original_response()
            return
        
        match view.select.values[0]:
            case "create":
                data: Panel = {
                    'name': None,
                    'description': None,
                    'active': False,
                    'channel': None,
                    'category': None,
                    'emoji': None,
                    'question': {},
                    'support_roles': [],
                    'ping_role': None,
                    'ticket_message': None,
                    'panel_message': None,
                    'nameing_scheme': None,
                }
                panel_view = TicketPanel(data, self.data, view.select.interaction)
                embed = await interaction.client.tickets.panel_embed(interaction.guild, data)
                await view.select.interaction.response.edit_message(embed=embed,view=panel_view)
                await panel_view.wait()
                if panel_view.value is False or panel_view.value is None:
                    return
                
                self.data['panels'][panel_view.data['name']] = panel_view.data
                await interaction.client.tickets.update_config(_id=self.data['_id'], data=self.data)
                await self.message.edit(embed=await interaction.client.tickets.get_config_embed(data=self.data))
            
            case "edit":
                panel_select = View()
                panel_select.value = False
                panel_select.select = Select_General(
                    interaction=interaction, placeholder="Select the panel you want to edit", options=[SelectOption(label=f"{k}", value=k, emoji=self.data['panels'][k]['emoji']) for k in self.data['panels'].keys()]
                )
                panel_select.add_item(panel_select.select)

                await view.select.interaction.response.edit_message(view=panel_select)

                await panel_select.wait()

                if panel_select.value is False or panel_select.value is None:
                    await interaction.delete_original_response()
                    return
                
                panel = self.data['panels'][panel_select.select.values[0]]
                panel_view = TicketPanel(panel, self.data, view.select.interaction)

                embed = await interaction.client.tickets.panel_embed(interaction.guild, panel)
                await panel_select.select.interaction.response.edit_message(embed=embed,view=panel_view)
                await panel_view.wait()
                if panel_view.value is False or panel_view.value is None:
                    return
                
                self.data['panels'][panel_view.data['name']] = panel_view.data
                await interaction.client.tickets.update_config(_id=self.data['_id'], data=self.data)
                await self.message.edit(embed=await interaction.client.tickets.get_config_embed(data=self.data))

            case "delete":
                panel_select = View()
                panel_select.value = False
                panel_select.select = Select_General(
                    interaction=interaction, placeholder="Select the panel you want to delete", options=[SelectOption(label=f"{k}", value=k) for k in self.data['panels'].keys()]
                )
                panel_select.add_item(panel_select.select)

                await view.select.interaction.response.edit_message(view=panel_select)

                await panel_select.wait()

                if panel_select.value is False or panel_select.value is None:
                    await interaction.delete_original_response()
                    return
                
                del self.data['panels'][panel_select.select.values[0]]
                await interaction.client.tickets.update_config(_id=self.data['_id'], data=self.data)
                await panel_select.select.interaction.edit_original_response(embed=await interaction.client.tickets.get_config_embed(data=self.data), view=None)

class TicketPanel(View):
    def __init__(self, data: Panel, config: TicketConfig, interaction: Interaction):
        self.data = data
        self.config = config
        self.value = False
        self.interaction = interaction
        super().__init__(timeout=300)

        if self.data['active'] is True:
            self.children[0].emoji = "<:tgk_toggle_on:1215647030974750750>"
        else:
            self.children[0].emoji = "<:tgk_toggle_off:1215647089610981478>"

        if self.data['name'] != None:
            self.children[1].disabled = True
            if self.data['name'].lower() == "partnership":
                self.children[4].disabled = True
        else:
            self.children[1].disabled = False

    @button(label="Active", style=discord.ButtonStyle.gray, emoji='<:toggle_on:1123932825956134912>')
    async def _active(self, interaction: Interaction, button: Button):
        self.data['active'] = True if self.data.get('active') is False else False
        button.emoji = "<:tgk_toggle_on:1215647030974750750>" if self.data['active'] is True else "<:tgk_toggle_on:1215647030974750750>"
        await interaction.response.edit_message(embed=await interaction.client.tickets.panel_embed(guild=interaction.guild, data=self.data), view=self)        

    @button(label="Name", style=discord.ButtonStyle.gray, emoji='<:tgk_id:1107614303575613520>')
    async def _name(self, interaction: Interaction, button: Button):
        modal = General_Modal(title='Panel Name', interaction=interaction)
        modal.name = TextInput(label='Enter the name of the panel', placeholder='Enter the name of the panel you want to create', min_length=3, max_length=100)
        if self.data.get('name') is not None: modal.name.default = self.data['name']
        modal.add_item(modal.name)
        await interaction.response.send_modal(modal)
        await modal.wait()

        if modal.value is False or modal.value is None:
            return
        
        if modal.name.value in self.config['panels'].keys():
            await interaction.response.send_message("Panel with this name already exists", ephemeral=True, delete_after=5)
            return
        
        self.data['name'] = modal.name.value
        button.disabled = True
        if self.data['name'].lower() == "partnership":
            self.children[4].disabled = True
        await modal.interaction.response.edit_message(embed=await interaction.client.tickets.panel_embed(guild=interaction.guild, data=self.data), view=self)

    @button(label="Description", style=discord.ButtonStyle.gray, emoji='<:tgk_entries:1124995375548338176>')
    async def _description(self, interaction: Interaction, button: Button):
        view = Description(name=self.data['name'], interaction=interaction, description=self.data.get('description'))
        embed = await view.update_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        await view.wait()
        if view.value is True:
            self.data['description'] = view.description
            await self.interaction.edit_original_response(embed=await interaction.client.tickets.panel_embed(guild=interaction.guild, data=self.data), view=self)

    @button(label="Ticket Message", style=discord.ButtonStyle.gray, emoji='<:tgk_message:1113527047373979668>')
    async def _ticket_message(self, interaction: Interaction, button: Button):
        view = Panel_Message(name=self.data['name'], interaction=interaction, message=self.data.get('ticket_message'))
        embed = await view.update_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        await view.wait()
        if view.value is False or view.value is None:
            return
        
        self.data['ticket_message'] = view.message
        await self.interaction.edit_original_response(embed=await interaction.client.tickets.panel_embed(guild=interaction.guild, data=self.data), view=self)

    @button(label="Questions", style=discord.ButtonStyle.gray, emoji='<:tgk_entries:1124995375548338176>')
    async def _questions(self, interaction: Interaction, button: Button):
        view = Panel_Question(data=self.data['question'], interaction=interaction)
        await interaction.response.send_message(view=view, ephemeral=True)

        await view.wait()
        if view.value is False or view.value is None:
            return
        
        self.data['questions'] = view.data
        await self.interaction.message.edit(embed=await interaction.client.tickets.panel_embed(guild=interaction.guild, data=self.data), view=self)

    @button(label='Roles', style=discord.ButtonStyle.gray, emoji='<:tgk_role:1073908306713780284>')
    async def _roles(self, interaction: Interaction, button: Button):
        view = Panel_Roles(data={"support_roles": self.data['support_roles'], "ping_role": self.data['ping_role']}, interaction=interaction)
        embed = await view.update_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        await view.wait()
        if view.value is False or view.value is None:
            return
        
        self.data['support_roles'] = view.data['support_roles']
        self.data['ping_role'] = view.data['ping_role']

        await self.interaction.edit_original_response(embed=await interaction.client.tickets.panel_embed(guild=interaction.guild, data=self.data), view=self)

    @button(label="Channels", style=discord.ButtonStyle.gray, emoji='<:tgk_channel:1073908465405268029>')
    async def _channel(self, interaction: Interaction, button: Button):
        view = Panel_Channel(interaction=interaction, current_channel={'channel': self.data['channel'], 'category': self.data['category'], 'nameing_scheme': self.data['nameing_scheme']}, name=self.data['name'])
        embed = await view.update_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        await view.wait()
        if view.value is True:
            self.data['channel'] = view.data['channel']
            self.data['category'] = view.data['category']
            self.data['nameing_scheme'] = view.data['nameing_scheme']
            await self.interaction.edit_original_response(embed=await interaction.client.tickets.panel_embed(guild=interaction.guild, data=self.data), view=self)

    @button(label="Emoji", style=discord.ButtonStyle.gray, emoji='<:tgk_fishing:1196665275794325504>')
    async def _emoji(self, interaction: Interaction, button: Button):
        modal = General_Modal(title=f"Editing {self.data['name']}'s Emoji", interaction=interaction)
        modal.name = TextInput(label="Enter/Edit Emoji",min_length=1, max_length=100, required=True)
        modal.name.default = self.data['emoji'] if self.data.get('emoji') is not None else ""
        modal.add_item(modal.name)
        await interaction.response.send_modal(modal)
        await modal.wait()

        if modal.value is False or modal.value is None:
            return
        
        self.data['emoji'] = modal.name.value
        await modal.interaction.response.edit_message(embed=await interaction.client.tickets.panel_embed(guild=interaction.guild, data=self.data), view=self)
    
    @button(label="Save", style=discord.ButtonStyle.gray, emoji='<:tgk_save:1210649255501635594>')
    async def _save(self, interaction: Interaction, button: Button):
        for chl in self.children: chl.disabled = True
        await interaction.response.edit_message(view=self, delete_after=5)
        self.value = True
        self.stop()

class Panel_Question(View):
    def __init__(self, data: dict, interaction: Interaction):
        self.data = data
        self.interaction = interaction
        self.value = False
        super().__init__(timeout=120)

    async def on_timeout(self):
        await self.interaction.delete_original_response()

    @button(label="Add Question", style=discord.ButtonStyle.gray, emoji='<:tgk_message_add:1073908702958059550>')
    async def _add(self, interaction: Interaction, button: Button):
        modal = General_Modal(title='Adding Question', interaction=interaction)
        modal.qes = TextInput(label='Enter the question',min_length=1, max_length=150, required=True, style=discord.TextStyle.long)
        modal.ans = TextInput(label='Enter the answer',min_length=1, max_length=1000, required=True, style=discord.TextStyle.long)
        modal.add_item(modal.qes)
        modal.add_item(modal.ans)
        await interaction.response.send_modal(modal)
        await modal.wait()

        if modal.value is False or modal.value is None:
            return
        
        embed = discord.Embed(description="", color=interaction.client.default_color)
        embed.description += f"### Q. {modal.qes.value}\n"
        embed.description += f"{modal.ans.value}\n"

        view = Confirm(user=interaction.user, timeout=30)
        await modal.interaction.response.send_message(embed=embed, ephemeral=True, view=view)
        view.message = await interaction.original_response()

        await view.wait()
        if view.value is False or view.value is None:
            return await view.interaction.response.edit_message(content="Canceled the question", view=None, delete_after=5)
        
        self.data[str(len(self.data.keys()) + 1)] = {'question': modal.qes.value, 'answer': modal.ans.value}
        await view.interaction.response.edit_message(content="Added the question", view=None, delete_after=5)


    @button(label="Edit Question", style=discord.ButtonStyle.gray, emoji='<:tgk_edit:1073902428224757850>')
    async def _edit(self, interaction: Interaction, button: Button):
        view = discord.ui.View()
        view.select = Select_General(interaction=interaction, placeholder="Select the question you want to edit", options=[SelectOption(label=f"{v['question']}", value=k) for k, v in self.data.items()])
        view.add_item(view.select)  

        await interaction.response.send_message(view=view, ephemeral=True)

        await view.wait()
        if view.value is False or view.value is None:
            return
        
        question = self.data[view.select.values[0]]
        modal = General_Modal(title='Editing Question', interaction=interaction)
        modal.qes = TextInput(label='Edit the question',min_length=1, max_length=150, required=True, style=discord.TextStyle.long)
        modal.ans = TextInput(label='Edit the answer',min_length=1, max_length=500, required=True, style=discord.TextStyle.long)
        modal.qes.default = question['question']
        modal.ans.default = question['answer']
        modal.add_item(modal.qes)
        modal.add_item(modal.ans)
        await interaction.response.send_modal(modal)
        await modal.wait()

        if modal.value is False or modal.value is None:
            return
        
        embed = discord.Embed(description="", color=interaction.client.default_color)
        embed.description += f"{modal.qes.value}\n"
        embed.description += f"{modal.ans.value}\n"

        view = Confirm(user=interaction.user, timeout=30)
        await modal.interaction.response.send_message(embed=embed, ephemeral=True, view=view)
        view.message = await interaction.original_response()

        await view.wait()
        if view.value is False or view.value is None:
            return await view.interaction.response.edit_message(content="Canceled the question", view=None, delete_after=5)
        
        self.data[view.select.values[0]] = {'question': modal.qes.value, 'answer': modal.ans.value}
        await view.interaction.response.edit_message(content="Edited the question", view=None, delete_after=5)

    @button(label="Delete Question", style=discord.ButtonStyle.gray, emoji='<:tgk_delete:1113517803203461222>')
    async def _delete(self, interaction: Interaction, button: Button):
        view = Select_General(interaction=interaction, placeholder="Select the question you want to delete", options=[SelectOption(label=f"{v['question']}", value=k) for k, v in self.data.items()])
        await interaction.response.send_message(view=view, ephemeral=True)

        await view.wait()
        if view.value is False or view.value is None:
            return
        
        question = self.data[view.select.values[0]]
        embed = discord.Embed(description=f"Are you sure you want to delete the question\n\n{question['question']}\n{question['answer']}", color=interaction.client.default_color)
        view = Confirm(user=interaction.user, timeout=30)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_response()

        await view.wait()
        if view.value is False or view.value is None:
            return
        
        del self.data[view.select.values[0]]
        await view.interaction.response.edit_message(content="Deleted the question", view=None, delete_after=5)

    @button(label="List Questions", style=discord.ButtonStyle.gray, emoji='<:tgk_entries:1124995375548338176>')
    async def _list(self, interaction: Interaction, button: Button):
        pages = []
        for k, v in self.data.items():
            pages.append(discord.Embed(description=f"**{v['question']}**\n\n{v['answer']}", color=interaction.client.default_color))
        await Paginator(interaction=interaction, pages=pages).start(embeded=True, quick_navigation=False, hidden=True)

    @button(label="Confirm", style=discord.ButtonStyle.gray, emoji='<:tgk_active:1082676793342951475>')
    async def _confirm(self, interaction: Interaction, button: Button):
        self.value = True
        for chl in self.children: chl.disabled = True
        await interaction.response.send_message("Updated the panel questions", ephemeral=True, delete_after=10, view=self)
        self.stop()
        
class Panel_Message(View):
    def __init__(self, name: str, interaction: Interaction, message: str=None):
        self.message = message
        self.name = name
        self.interaction = interaction
        self.value = False
        super().__init__(timeout=120)

    async def on_timeout(self):
        await self.interaction.delete_original_response()

    async def update_embed(self):
        embed = discord.Embed(description="", color=self.interaction.client.default_color)
        embed.description += f"<:tgk_description:1215649279360897125> `Ticket Message`\n\n"
        embed.description += f"```\n{self.message}\n```" if self.message is not None else "No message provided"

        return embed
    
    @button(label="Edit", style=discord.ButtonStyle.gray, emoji='<:tgk_edit:1073902428224757850>')
    async def _edit(self, interaction: Interaction, button: Button):
        modal = General_Modal(title=f"Editing {self.name}'s ticket message", interaction=interaction)
        modal.name = TextInput(label='Edit/Add the message',min_length=1, max_length=1000, required=True, style=discord.TextStyle.long)
        if self.message is not None: modal.name.default = self.message
        modal.add_item(modal.name)
        await interaction.response.send_modal(modal)
        await modal.wait()

        if modal.value is False or modal.value is None:
            await self.interaction.delete_original_response()
            return
        
        self.message = modal.name.value
        self.children[1].disabled = False
        await modal.interaction.response.edit_message(view=self, embed=await self.update_embed())

    @button(label="Confirm", style=discord.ButtonStyle.gray, emoji='<:tgk_active:1082676793342951475>')
    async def _confirm(self, interaction: Interaction, button: Button):
        self.value = True
        for chl in self.children: chl.disabled = True
        await interaction.response.edit_message(view=self, delete_after=10)
        self.stop()
                         
class Panel_Roles(View):
    def __init__(self, data: dict[str, list[int]], interaction: Interaction):
        self.data = data
        self.value = False
        self.interaction = interaction
        super().__init__(timeout=120)

    async def on_timeout(self):
        await self.interaction.delete_original_response()
    
    async def update_embed(self):
        embed = discord.Embed(description="", color=self.interaction.client.default_color)
        args = await get_formated_embed(["Support Roles", "Ping Roles"])
        embed.description += f"<:tgk_role:1073908306713780284> `Panel Roles`\n\n"
        embed.description += f"{await get_formated_field(guild=self.interaction.guild, name=args['Support Roles'], type='role', data=self.data['support_roles'])}\n"
        embed.description += f"{await get_formated_field(guild=self.interaction.guild, name=args['Ping Roles'], type='role', data=self.data['ping_role'])}\n"
        embed.add_field
        return embed

    @select(placeholder="Select the role you want to add/remove from the panel", cls=discord.ui.RoleSelect, min_values=1, max_values=10)
    async def _support_roles(self, interaction: Interaction, select: Select):
        for role in select.values:
            if role.id in self.data:
                self.data['support_roles'].remove(role.id)
            else:
                self.data['support_roles'].append(role.id)

        await interaction.response.edit_message(embed=await self.update_embed(), view=self)

    
    @select(placeholder="Select the role you want to ping when a ticket is created", cls=discord.ui.RoleSelect, min_values=1, max_values=1)
    async def _ping_role(self, interaction: Interaction, select: Select):
        self.data['ping_role'] = select.values[0].id if self.data['ping_role'] != select.values[0].id else None
        await interaction.response.edit_message(embed=await self.update_embed(), view=self)

    @button(label="Confirm", style=discord.ButtonStyle.gray, emoji='<:tgk_active:1082676793342951475>')
    async def _confirm(self, interaction: Interaction, button: Button):
        self.value = True
        for chl in self.children: chl.disabled = True
        await interaction.response.edit_message(content="Updated the panel roles", delete_after=10, view=self)
        self.stop()
        
class Description(View):
    def __init__(self, name: str, interaction: Interaction, description: str=None):
        self.description = description
        self.name = name
        self.interaction = interaction
        self.value = False
        super().__init__(timeout=120)

    async def on_timeout(self):
        await self.interaction.delete_original_response()
    
    async def update_embed(self):
        embed = discord.Embed(description="", color=self.interaction.client.default_color)
        embed.description += f"<:tgk_description:1215649279360897125> `{self.name}'s Description`\n\n"
        embed.description += f"```\n{self.description}\n```" if self.description is not None else "No description provided"
        return embed

    @button(label="Edit", style=discord.ButtonStyle.gray, emoji='<:tgk_edit:1073902428224757850>')
    async def _edit(self, interaction: Interaction, button: Button):
        modal = General_Modal(title=f"Editing {self.name} Panel's Description", interaction=interaction)
        modal.name = TextInput(label='Enter/Edit Description',min_length=1, max_length=500, required=True, style=discord.TextStyle.long)
        if self.description is not None: modal.name.default = self.description
        modal.add_item(modal.name)
        await interaction.response.send_modal(modal)
        await modal.wait()

        if modal.value is False or modal.value is None:
            await self.interaction.delete_original_response()
            return
        
        self.description = modal.name.value
        self.children[1].disabled = False

        embed = await self.update_embed()
        await modal.interaction.response.edit_message(view=self, embed=embed)

    @button(label="Confirm", style=discord.ButtonStyle.gray, emoji='<:tgk_active:1082676793342951475>')
    async def _confirm(self, interaction: Interaction, button: Button):
        self.value = True
        for chl in self.children: chl.disabled = True
        await interaction.response.edit_message(view=self, delete_after=10)
        self.stop()

class Panel_Channel(View):
    def __init__(self, interaction: Interaction, current_channel: dict, name: str):
        self.data = current_channel
        self.name = name
        self.interaction = interaction
        self.value = False
        super().__init__(timeout=120)

    async def on_timeout(self):
        await self.interaction.delete_original_response()

    async def update_embed(self):
        embed = discord.Embed(description="", color=self.interaction.client.default_color)
        args = await get_formated_embed(["Channel", "Category", "Naming Scheme"])
        embed.description += f"<:tgk_channel:1073908465405268029> `Channel Config`\n\n"
        embed.description += f"{await get_formated_field(guild=self.interaction.guild, name=args['Channel'], type='channel', data=self.data['channel'])}\n"
        embed.description += f"{await get_formated_field(guild=self.interaction.guild, name=args['Category'], type='channel', data=self.data['category'])}\n"        
        embed.description += f"{await get_formated_field(guild=self.interaction.guild, name=args['Naming Scheme'], type='str', data=self.data['nameing_scheme'])}\n"
        return embed

    @select(placeholder="Select the channel you want to use as the panel channel", cls=discord.ui.ChannelSelect, min_values=1, max_values=1, channel_types=[discord.ChannelType.text])
    async def _channel(self, interaction: Interaction, select: Select):
        select.disabled = True
        self.data['channel'] = select.values[0].id
        await interaction.response.edit_message(embed=await self.update_embed(), view=self)

    @select(placeholder="Select the category you want to use as the panel category", cls=discord.ui.ChannelSelect, min_values=1, max_values=1, channel_types=[discord.ChannelType.category])
    async def _category(self, interaction: Interaction, select: Select):
        select.disabled = True
        self.data['category'] = select.values[0].id
        await interaction.response.edit_message(embed=await self.update_embed(), view=self)

    @button(label="Ticket Nameing Scheme", style=discord.ButtonStyle.gray, emoji='<:tgk_edit:1073902428224757850>')
    async def _nameing_scheme(self, interaction: Interaction, button: Button):
        modal = General_Modal(title='Ticket Nameing Scheme', interaction=interaction)
        modal.name = TextInput(label='Enter the nameing scheme', placeholder=f'Enter the nameing scheme you want to use eg. (⸝⸝🎫。)', min_length=3, max_length=100)
        if self.data.get('nameing_scheme') is not None: modal.name.default = self.data['nameing_scheme']
        modal.add_item(modal.name)

        await interaction.response.send_modal(modal)
        await modal.wait()

        if modal.value is False or modal.value is None:
            return
        
        self.data['nameing_scheme'] = modal.name.value
        await modal.interaction.response.edit_message(view=self, embed=await self.update_embed())

    @button(label="Confirm", style=discord.ButtonStyle.gray, emoji='<:tgk_active:1082676793342951475>')
    async def _confirm(self, interaction: Interaction, button: Button):
        self.value = True
        for btn in self.children: btn.disabled = True
        await interaction.response.edit_message(content="Updated the panel channel", delete_after=5)
        self.stop()

class Channel_Config(View):
    def __init__(self):
        super().__init__(timeout=120)
        self.value = False
        self.data = {
            'default_category': None,
            'default_channel': None,
            'log_channel': None,
            'transcript_channel': None,
        }
    
    @select(placeholder="Select Default Ticket Category", cls=discord.ui.ChannelSelect, min_values=1, max_values=1, channel_types=[discord.ChannelType.category])
    async def _default_category(self, interaction: Interaction, select: Select):
        select.disabled = True
        self.data['default_category'] = select.values[0]
        await interaction.response.edit_message(view=self)
    
    @select(placeholder="Select Default Ticket Panel Channel", cls=discord.ui.ChannelSelect, min_values=1, max_values=1, channel_types=[discord.ChannelType.text])
    async def _default_panel(self, interaction: Interaction, select: Select):
        select.disabled = True
        self.data['default_channel'] = select.values[0]
        await interaction.response.edit_message(view=self)

    @select(placeholder="Select Log Channel", cls=discord.ui.ChannelSelect, min_values=1, max_values=1, channel_types=[discord.ChannelType.text])
    async def _log_channel(self, interaction: Interaction, select: Select):
        select.disabled = True
        self.data['log_channel'] = select.values[0]
        await interaction.response.edit_message(view=self)

    @select(placeholder="Select Transcript Channel", cls=discord.ui.ChannelSelect, min_values=1, max_values=1, channel_types=[discord.ChannelType.text])
    async def _transcript_channel(self, interaction: Interaction, select: Select):
        select.disabled = True
        self.data['transcript_channel'] = select.values[0]
        await interaction.response.edit_message(view=self)

    @button(label="Ticket Nameing Scheme", style=discord.ButtonStyle.gray, emoji='<:tgk_edit:1073902428224757850>')
    async def _nameing_scheme(self, interaction: Interaction, button: Button):
        modal = General_Modal(title='Ticket Nameing Scheme', interaction=interaction)
        modal.name = TextInput(label='Enter the nameing scheme', placeholder=f'Enter the nameing scheme you want to use eg. (⸝⸝🎫。)', min_length=3, max_length=100)
        if self.data.get('nameing_scheme') is not None: modal.name.default = self.data['nameing_scheme']
        modal.add_item(modal.name)

        await interaction.response.send_modal(modal)
        await modal.wait()

        if modal.value is False or modal.value is None:
            return
        
        self.data['nameing_scheme'] = modal.name.value
        await modal.interaction.response.edit_message(view=self)        

    @button(label="Confirm", style=discord.ButtonStyle.gray, emoji='<:tgk_active:1082676793342951475>')
    async def _confirm(self, interaction: Interaction, button: Button):
        embed = discord.Embed(description="", color=interaction.client.default_color)
        keys = ['default_category', 'default_channel', 'log_channel', 'transcript_channel', 'nameing_scheme']

        for key in keys:
            if self.data.get(key) is not None:
                embed.description += f"{key.replace('_', ' ').title()}: {self.data[key].mention}\n"

        await interaction.response.edit_message(embed=embed, view=None)
        self.value = True
        self.stop()

# NOTE: Ticket Creation View

class Panels(discord.ui.View):
    def __init__(self, panels: Dict[str, Panel] | List[Panel], guild_id: int):
        self.panels = panels
        super().__init__(timeout=None)
        if isinstance(panels, dict):
            for panel in self.panels:
                self.add_item(PanelButton(custom_id=f"{guild_id}:panel:{panels[panel]['name']}", label=panels[panel]['name'], emoji=panels[panel]['emoji']))
        elif isinstance(panels, list):
            for panel in self.panels:
                self.add_item(PanelButton(custom_id=f"{guild_id}:panel:{panel['name']}", label=panel['name'], emoji=panel['emoji']))
        else:
            raise TypeError("Invalid type for panels")
    
    # async def on_error(self, interaction: Interaction, error: Exception, item: Item):
    #     try:
    #         await interaction.response.send_message(embed=discord.Embed(description=f"```py\n{traceback.format_exception(type(error), error, error.__traceback__, 4)}\n```", color=discord.Color.red()), ephemeral=True)
    #     except :
    #         await interaction.followup.send(embed=discord.Embed(description=f"```py\n{traceback.format_exception(type(error), error, error.__traceback__, 4)}\n```", color=discord.Color.red()), ephemeral=True)

class TicketQestionDropDown(View):
    def __init__(self, data: Qestion):
        self.data = data
        self.create_ticket = False
        super().__init__(timeout=120)
        self.dropdown: Select = self.children[0]
        self.qestions = [SelectOption(label=f"{value['question']}", value=key) for key, value in self.data.items()]
        self.qestions.append(SelectOption(label="None of the above", value="none"))
        self.dropdown.options = self.qestions
        self.interaction = None

    async def on_timeout(self):
        self.create_ticket = False
        self.stop()

    @select(placeholder="Dose the following question apply to you?", min_values=1, max_values=1, options=[None])
    async def _question(self, interaction: Interaction, select: Select):
        if select.values[0] != "none":
            self.create_ticket = False
            embed = discord.Embed(color=interaction.client.default_color)
            qestion = self.data[select.values[0]]
            embed.add_field(name=f"Q. {qestion['question']}", value=f"{qestion['answer']}", inline=False)
            
            await interaction.response.edit_message(embed=embed, view=None)
        else:
            self.create_ticket = True
            self.interaction = interaction
        self.stop()

class PanelButton(discord.ui.Button):
    def __init__(self, custom_id: str, label: str, emoji: str=None):
        super().__init__(style=discord.ButtonStyle.gray, label=label, emoji=emoji, custom_id=custom_id)

    async def callback(self, interaction: Interaction):
        config: TicketConfig = await interaction.client.tickets.get_config(interaction.guild_id)
        try:
            panel: Panel = config['panels'][self.custom_id.split(":")[2]]
        except KeyError:
            return await interaction.response.send_message("This panel does not exist", ephemeral=True)
        
        extra_content = {}

        if panel['active'] is False:
            self.disabled = True
            await interaction.response.send_message("This ticket panel is disabled by the administrator", ephemeral=True)
            await interaction.edit_original_response(view=self.view)

        if panel['name'].lower() == "partnership":
            modal = PartnerShipModal(interaction=interaction)
            await interaction.response.send_modal(modal)
            await modal.wait()

            if modal.data == {}:
                return
            else:
                await modal.interaction.response.send_message(content=f"<a:TGK_loading:1222135771935412287> Please wait while we create {self.custom_id.split(':')[2]}'s ticket", ephemeral=True)
                interaction = modal.interaction
                invite = modal.data['invite'].split("/")[-1]
                try:
                    invite = await interaction.client.fetch_invite(invite)
                except discord.errors.NotFound:
                    return await modal.interaction.edit_original_response(content="<:tgk_deactivated:1082676877468119110> The invite you provided is invalid, please try again", view=None)
                extra_content['pinfo'] = ""
                extra_content['pinfo'] += f"**Server Name:** {invite.guild.name}\n**Server Aproximate Members:** {invite.approximate_member_count}\n**Server ID:** `{invite.guild.id}`\n**Server Invite:** {invite}\n**Partnership Type**: {modal.ptype.value}"

        elif panel['question'] != {}:
            QestionView = TicketQestionDropDown(data=panel['question'])
            await interaction.response.send_message(view=QestionView, ephemeral=True, delete_after=600)
            await QestionView.wait()
            interaction = QestionView.interaction
            if QestionView.create_ticket is False:
                return
            
        await interaction.response.send_message(content=f"<a:TGK_loading:1222135771935412287> Please wait while we create {self.custom_id.split(':')[2]}'s ticket", ephemeral=True)
        
        if panel['category'] == None:
            category = interaction.guild.get_channel(config['default_category'])
        else:
            category = interaction.guild.get_channel(panel['category'])

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True, embed_links=True, add_reactions=True)
        }
        for role in panel['support_roles']:
            role = interaction.guild.get_role(role)
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True, embed_links=True, add_reactions=True)

        TicketName = f"{panel['nameing_scheme']}{interaction.user.name}" if panel['nameing_scheme'] != None else f"{config['nameing_scheme']['unlocked']} {interaction.user.name}"

        TicketChannel = await interaction.guild.create_text_channel(name=TicketName, category=category, overwrites=overwrites, topic=f"Ticket created by {interaction.user.name}", reason="Ticket Creation")
        TicketEmbed = discord.Embed(title=f"{panel['name']} Ticket", description=panel['ticket_message'], color=interaction.client.default_color)
        TicketEmbed.set_footer(text=f"Ticket ID: {TicketChannel.id}")
        TicketMessage = await TicketChannel.send(embed=TicketEmbed, content=f"{interaction.user.mention} {interaction.guild.get_role(panel['ping_role']).mention if panel['ping_role'] is not None else ''}", view=TicketControl())

        if extra_content != {}:
            for key, value in extra_content.items():
                await TicketChannel.send(value)

        await TicketMessage.pin()
        TicketData: Ticket = {
            '_id': TicketChannel.id,
            'user_id': interaction.user.id,
            'channel_id': TicketChannel.id,
            'panel': panel['name'],
            'status': 'open',
            'added_roles': [],
            'added_users': [],
            'anonymous': {
                'status': False,
                'thread_id': None,
            },
        }
        await interaction.client.tickets.ticket.insert(TicketData)
        view = View()
        view.add_item(discord.ui.Button(label="Jump to Ticket", style=discord.ButtonStyle.link, url=TicketMessage.jump_url))
        await interaction.edit_original_response(content=f"Ticket created in {TicketChannel.mention}", view=view)


class TicketControl(View):
    def __init__(self):
        super().__init__(timeout=None)    

    @button(label="Open", style=discord.ButtonStyle.gray, emoji='<:tgk_unlock:1072851439161983028>', custom_id="ticket:open")
    async def _open(self, interaction: Interaction, button: Button):
        ticket_data: Ticket = await interaction.client.tickets.ticket.find({'_id': interaction.channel.id})
        if not ticket_data:
            return await interaction.response.send_message("This is not a ticket channel", ephemeral=True)
        if ticket_data['status'] == "open":
            return await interaction.response.send_message("This ticket is already open", ephemeral=True)
        ticket_data['status'] = "open"
        
        embed = discord.Embed(description="<a:loading:998834454292344842> Opening the ticket", color=interaction.client.default_color)
        await interaction.response.send_message(embed=embed)
        overwrite = discord.PermissionOverwrite(view_channel=True)

        for role in ticket_data['added_roles']: await interaction.channel.set_permissions(interaction.guild.get_role(role), overwrite=overwrite)
        for user in ticket_data['added_users']: await interaction.channel.set_permissions(interaction.guild.get_member(user), overwrite=overwrite)

        ticket_owner = interaction.guild.get_member(ticket_data['user_id'])
        if not ticket_owner:
            return await interaction.edit_original_response(embed=discord.Embed(description="Unable to find the ticket owner in the server, they might have left the server", color=discord.Color.red()))
        
        await interaction.channel.set_permissions(ticket_owner, overwrite=overwrite)
        await interaction.client.tickets.ticket.update(ticket_data)

        config: TicketConfig = await interaction.client.tickets.get_config(interaction.guild.id)
        name = f"{config['panels'][ticket_data['panel']]['nameing_scheme']}{ticket_owner.name}" if config['panels'][ticket_data['panel']]['nameing_scheme'] != None else f"{config['nameing_scheme']['unlocked']}{ticket_owner.name}"

        await interaction.channel.edit(name=name)
        await interaction.edit_original_response(embed=discord.Embed(description=f"Ticket opended by the {interaction.user.mention}", color=interaction.client.default_color))

    @button(label="Close", style=discord.ButtonStyle.gray, emoji='<:tgk_lock:1072851190213259375>', custom_id="ticket:close")
    async def _close(self, interaction: Interaction, button: Button):
        ticket_data: Ticket = await interaction.client.tickets.ticket.find({'_id': interaction.channel.id})

        if not ticket_data:
            return await interaction.response.send_message("This is not a ticket channel", ephemeral=True)
        if ticket_data['status'] == "closed":
            return await interaction.response.send_message("This ticket is already closed", ephemeral=True)
        ticket_data['status'] = "closed"

        embed = discord.Embed(description="<a:loading:998834454292344842> Closing the ticket", color=interaction.client.default_color)
        await interaction.response.send_message(embed=embed)
        overwrite = discord.PermissionOverwrite(view_channel=False)

        for role in ticket_data['added_roles']: await interaction.channel.set_permissions(interaction.guild.get_role(role), overwrite=overwrite)
        for user in ticket_data['added_users']: await interaction.channel.set_permissions(interaction.guild.get_member(user), overwrite=overwrite)

        ticket_owner = interaction.guild.get_member(ticket_data['user_id'])
        if not ticket_owner:
            return await interaction.edit_original_response(embed=discord.Embed(description="Unable to find the ticket owner in the server, they might have left the server", color=discord.Color.red()))
        
        await interaction.channel.set_permissions(ticket_owner, overwrite=overwrite)
        await interaction.client.tickets.ticket.update(ticket_data)

        config = await interaction.client.tickets.get_config(interaction.guild.id)
        name = f"{config['nameing_scheme']['locked']}{ticket_owner.name}"
        await interaction.channel.edit(name=name)
        await interaction.edit_original_response(embed=discord.Embed(description=f"Ticket closed by the {interaction.user.mention}", color=interaction.client.default_color))

    @button(label="Delete", style=discord.ButtonStyle.gray, emoji='<:tgk_delete:1113517803203461222>', custom_id="ticket:delete")
    async def _delete(self, interaction: Interaction, button: Button):
        ticket_data: Ticket = await interaction.client.tickets.ticket.find({'_id': interaction.channel.id})
        if not ticket_data:
            return await interaction.response.send_message("This is not a ticket channel", ephemeral=True)
        
        ticket_owner = interaction.guild.get_member(ticket_data['user_id'])
        if not ticket_owner:
            ticket_owner = await interaction.client.fetch_user(ticket_data['user_id'])

        timestemp = datetime.datetime.now() + datetime.timedelta(seconds=20)
        embed = discord.Embed(description=f"Deleting ticket in <t:{round(timestemp.timestamp())}:R>, {interaction.user.mention} use button below to cancel", color=interaction.client.default_color)
        ConfimView = Confirm(user=interaction.user, timeout=20)
        ConfimView.children[0].label = "Cancel"
        ConfimView.remove_item(ConfimView.children[1])

        await interaction.response.send_message(embed=embed, view=ConfimView, ephemeral=False)
        ConfimView.message = await interaction.original_response()
        await ConfimView.wait()

        if ConfimView.value is True: return await ConfimView.interaction.response.edit_message(embed=discord.Embed(description="Ticket deletion canceled", color=interaction.client.default_color), view=None)
        await interaction.edit_original_response(embed=discord.Embed(description="<a:TGK_loading:1222135771935412287> Crating a transcript and deleting the ticket", color=interaction.client.default_color), view=None)

        Config: TicketConfig = await interaction.client.tickets.get_config(interaction.guild.id)
        TranscriptChannel = interaction.guild.get_channel(Config['transcript_channel'])

        if Config['transcript_channel'] is None or not isinstance(TranscriptChannel, discord.TextChannel):
            await interaction.client.tickets.ticket.delete(ticket_data['_id'])
            await interaction.channel.delete()
            return
        
        TicketMessages = [message async for message in interaction.channel.history(limit=None)]
        TranscriptFile = await chat_exporter.raw_export(channel=interaction.channel, messages=TicketMessages, tz_info="Asia/Kolkata", guild=interaction.guild, bot=interaction.client, support_dev=False)
        TranscriptFile = discord.File(io.BytesIO(TranscriptFile.encode()), filename=f"transcript-{ticket_owner.name}-{ticket_data['panel']}.html")

        TranscriptMessage = await TranscriptChannel.send(file=TranscriptFile, content=f"**Channel**: `{interaction.channel.name}`\n**Ticket Owner**: {ticket_owner.mention}\n**Panel**: {ticket_data['panel']}")
        TranscriptUrl = urllib.parse.quote(TranscriptMessage.attachments[0].url, safe="")
        linkView =  Refresh_Trancsript()
        linkView.add_item(discord.ui.Button(label="View Transcript", url=f"https://api.natbot.xyz/transcripts?url={TranscriptUrl}", style=discord.ButtonStyle.url, emoji="<:tgk_link:1105189183523401828>"))
        await TranscriptMessage.edit(view=linkView)

        await interaction.client.tickets.ticket.delete(ticket_data['_id'])
        await interaction.channel.delete()
    
    @button(label="Annonymous", style=discord.ButtonStyle.gray, emoji='<:tgk_amongUs:1103542462628253726>', custom_id="ticket:anonymous")
    async def _anonymous(self, interaction: Interaction, button: Button):
        ticket_data: Ticket = await interaction.client.tickets.ticket.find({'_id': interaction.channel.id})
        if not ticket_data:
            return await interaction.response.send_message("This is not a ticket channel", ephemeral=True)
        
        if ticket_data['anonymous']['status'] == True:
            thread = interaction.guild.get_thread(ticket_data['anonymous']['thread_id'])
            await thread.add_user(interaction.user)
            await interaction.response.send_message(embed=discord.Embed(description=f"Added you to the tickets private thread", color=interaction.client.default_color), ephemeral=True)
        else:
            thread = await interaction.channel.create_thread(name=f"🐱‍👤 Secret Chat", auto_archive_duration=60, type=discord.ChannelType.private_thread)
            await thread.send("please be advised that this thread is now designated as private and restricted only to moderators and higher-ups. Thank you for your understanding and cooperation in respecting the privacy of this thread.")
            await thread.add_user(interaction.user)
            ticket_data['anonymous']['status'] = True
            ticket_data['anonymous']['thread_id'] = thread.id
            await interaction.client.tickets.ticket.update(ticket_data)
            await interaction.response.send_message(embed=discord.Embed(description=f"Created a private thread for the ticket", color=interaction.client.default_color), ephemeral=True)


class Refresh_Trancsript(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Refresh", style=discord.ButtonStyle.gray, emoji="<:tgk_refresh:1171330950416842824>", custom_id="transcript:refresh")
    async def refresh(self, interaction: Interaction, button: Button):
        if len(interaction.message.attachments) <= 0: 
            await interaction.response.send_message("No transcript found", ephemeral=True, delete_after=5)
        
        attachment = interaction.message.attachments[0]
        attachment_url = urllib.parse.quote(attachment.url, safe="")
        transcript_url = f"https://api.natbot.xyz/transcripts?url={attachment_url}"
        view = Refresh_Trancsript()
        view.add_item(discord.ui.Button(label="View Transcript", url=transcript_url, style=discord.ButtonStyle.url, emoji="<:tgk_link:1105189183523401828>"))
        await interaction.response.edit_message(view=view)


class PartnerShipModal(discord.ui.Modal):
    def __init__(self, interaction: Interaction):
        self.interaction = interaction
        self.data = {}
        super().__init__(timeout=120, title=f"Partnership form for {interaction.guild.name}")
    
    server = TextInput(label="Enter the server name", min_length=1, max_length=100, required=True)
    invite = TextInput(label="Enter the server invite", min_length=1, max_length=100, required=True)
    ptype = TextInput(label="Enter the partnership type", min_length=1, max_length=100, required=True)

    async def on_submit(self, interaction: Interaction):
        self.data = {
            'server': self.server.value,
            'invite': self.invite.value,
            'type': self.ptype.value,
        }
        self.interaction = interaction
        self.stop()
