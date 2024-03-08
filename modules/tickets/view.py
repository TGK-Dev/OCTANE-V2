import discord
import traceback
from discord import Interaction, SelectOption, app_commands
from discord.ui import View, Button, button, TextInput, Item, Select, select
from utils.views.selects import Role_select, Select_General, Channel_select
from utils.views.modal import General_Modal
from utils.views.buttons import Confirm
from utils.paginator import Paginator
from utils.embed import get_formated_embed, get_formated_field
from .db import TicketConfig, Panel

class TicketConfig_View(View):
    def __init__(self, user:discord.Member, data: TicketConfig, message: discord.Message=None):
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
        
        keys = ['default_category', 'default_channel', 'log_channel', 'transcript_channel']
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
                    interaction=interaction, placeholder="Select the panel you want to edit", options=[SelectOption(label=f"{k}", value=k) for k in self.data['panels'].keys()]
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
        view = Panel_Channel(interaction=interaction, current_channel={'channel': self.data['channel'], 'category': self.data['category']}, name=self.data['name'])
        embed = await view.update_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        await view.wait()
        if view.value is True:
            self.data['channel'] = view.data['channel']
            self.data['category'] = view.data['category']
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
        embed.description += f"{modal.qes.value}\n"
        embed.description += f"{modal.ans.value}\n"

        view = Confirm(user=interaction.user, timeout=30)
        await modal.interaction.response.send_message(embed=embed, ephemeral=True, view=view)
        view.message = await interaction.original_response()

        await view.wait()
        if view.value is False or view.value is None:
            return
        
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
            return
        
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
        await interaction.response.send_message("Updated the panel questions", ephemeral=True, delete_after=5)
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
        await interaction.response.edit_message(view=self)
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
        await interaction.response.edit_message(content="Updated the panel roles", delete_after=5, view=None)
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
        await interaction.response.edit_message(view=self)
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
        args = await get_formated_embed(["Channel", "Category"])
        embed.description += f"<:tgk_channel:1073908465405268029> `Channel Config`\n\n"
        embed.description += f"{await get_formated_field(guild=self.interaction.guild, name=args['Channel'], type='channel', data=self.data['channel'])}\n"
        embed.description += f"{await get_formated_field(guild=self.interaction.guild, name=args['Category'], type='channel', data=self.data['category'])}\n"        
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

    @button(label="Confirm", style=discord.ButtonStyle.gray, emoji='<:tgk_active:1082676793342951475>')
    async def _confirm(self, interaction: Interaction, button: Button):
        self.value = True
        await interaction.response.send_message("Updated the panel channel", ephemeral=True, delete_after=5)
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

    @button(label="Confirm", style=discord.ButtonStyle.gray, emoji='<:tgk_active:1082676793342951475>')
    async def _confirm(self, interaction: Interaction, button: Button):
        embed = discord.Embed(description="", color=interaction.client.default_color)
        keys = ['default_category', 'default_channel', 'log_channel', 'transcript_channel']

        for key in keys:
            if self.data.get(key) is not None:
                embed.description += f"{key.replace('_', ' ').title()}: {self.data[key].mention}\n"

        await interaction.response.edit_message(embed=embed, view=None)
        self.value = True
        self.stop()