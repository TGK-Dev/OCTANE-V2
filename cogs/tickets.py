import discord
from discord.ext import commands
from discord import app_commands
from discord.app_commands import Group, Choice
from utils.transformer import MultipleMember
from utils.db import Document
from typing import Union, Literal, List
from utils.views import ticket_system

class Ticket_DB:
    def __init__(self, bot, Document):
        self.config: Document = Document(bot.db, "tickets_config")
        self.tickets: Document = Document(bot.db, "tickets")

panel_templates = {
    "partnership": { 'key': 'partnership', 'support_roles': [], 'color': 'blurple', 'emoji':'<a:Partner:1000335814481416202>', 'ping_role': None, 'created_by': None, 'description': 'Used for heist partnership deals only!\nMake sure to checkout requirements first.' },

}

class Ticket(commands.GroupCog, name="ticket"):
    def __init__(self, bot):
        self.bot = bot
        self.bot.tickets = Ticket_DB(self.bot, Document)
    
    async def panel_auto_complete(self, interaction: discord.Interaction, current: str) -> List[Choice[str]]:
        ticket_system = await self.bot.tickets.config.find(interaction.guild.id)
        if ticket_system is None: return [Choice(name="No panels", value="No panels")]
        return [
            Choice(name=panel, value=panel)
            for panel in ticket_system['panels'].keys()
        ]
    
    panel = Group(name="panel", description="Ticket panel commands")
    
    @commands.Cog.listener()
    async def on_ready(self):
        ticket_configs = await self.bot.tickets.config.get_all()
        for ticket_config in ticket_configs:
            if ticket_config['panels'] is None: continue
            panel_view = ticket_system.Panel_View()
            for panel in ticket_config['panels'].keys():
                panel = ticket_config['panels'][panel]
                style = discord.ButtonStyle.gray
                if panel['color'] == "blurple": style = discord.ButtonStyle.blurple
                elif panel['color'] == "green": style = discord.ButtonStyle.green
                elif panel['color'] == "red": style = discord.ButtonStyle.red
                emoji = panel['emoji'] if panel['emoji'] is not None else None
                button = ticket_system.Panel_Button(label=panel['key'].capitalize(), style=style, emoji=emoji, custom_id=f"{ticket_config['_id']}-{panel['key']}")
                panel_view.add_item(button)
                self.bot.add_view(panel_view)
                
        self.bot.add_view(ticket_system.Panel_View())

    @app_commands.command(name="config", description="Configure ticket system")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(option="Show/Edit")
    async def ticket_config(self, interaction: discord.Interaction, option: Literal['show', 'edit']="show"):
        ticket_config = await self.bot.tickets.config.find(interaction.guild.id)
        if ticket_config is None:
            ticket_config = {'_id': interaction.guild.id,'category': None,'channel': None,'logging': None,'panels': {},'last_panel_message_id': None, 'transcript': None}
            await self.bot.tickets.config.insert(ticket_config)
        
        embed = discord.Embed(title="Ticket Config", color=0x363940, description="")
        embed.description += f"**Category:**" + (f" <#{ticket_config['category']}>" if ticket_config['category'] is not None else "`None`") + "\n"
        embed.description += f"**Channel:**" + (f" <#{ticket_config['channel']}>" if ticket_config['channel'] is not None else "`None`") + "\n"
        embed.description += f"**Logging:**" + (f" <#{ticket_config['logging']}>" if ticket_config['logging'] is not None else "`None`") + "\n"
        embed.description += f"**Transcript:**" + (f" <#{ticket_config['transcript']}>" if ticket_config['transcript'] is not None else "`None`") + "\n"
        embed.description += f"**Panel Message:**" + (f" {ticket_config['last_panel_message_id']}" if ticket_config['last_panel_message_id'] is not None else "`None`") + "\n"
        embed.description += f"**Panels:**" + (f"`{len(ticket_config['panels'])}`" if ticket_config['panels'] is not None else "`0`") + "\n"
        
        if option == "show":
            await interaction.response.send_message(embed=embed)
        elif option == "edit":
            view = ticket_system.Config_Edit(interaction.user, ticket_config)
            await interaction.response.send_message(embed=embed, view=view)
            view.message = await interaction.original_response()
            await view.wait()
            if view.value:
                print(view.data)
                await self.bot.tickets.config.update(view.data)
        
    @panel.command(name="create", description="Create a ticket panel")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(name="name")
    @app_commands.describe(template="Select a template to use")
    @app_commands.choices(template=[app_commands.Choice(name="Partnership", value="partnership")])
    async def create_panel(self, interaction: discord.Interaction, name: str, template: app_commands.Choice[str]=None):
        ticket_config = await self.bot.tickets.config.find(interaction.guild.id)
        if ticket_config is None:
            ticket_config = {'_id': interaction.guild.id,'category': None,'channel': None,'logging': None,'panels': {},'last_panel_message_id': None, 'transcript': None}
            await self.bot.tickets.config.insert(ticket_config)
        if name in ticket_config['panels'].keys(): return await interaction.response.send_message("This panel already exists", ephemeral=True, delete_after=5)        
        
        if template is None:
            panel_data = {'key': name, 'support_roles': [], "ping_role": None, 'created_by': interaction.user.id, 'description': None, 'emoji': None, 'color': None, 'modal': {'type': 'short', 'question': "Please describe your issue"}}
        else:
            panel_data = panel_templates[template.value]

        embed = discord.Embed(title=f"Settings for Panel: {name}", color=0x363940, description="")
        embed.description += f"**Support Roles:** {', '.join([f'<@&{role}>' for role in panel_data['support_roles']]) if len(panel_data['support_roles']) > 0 else '`None`'}\n"
        embed.description += f"**Ping Role:**" + (f" <@&{panel_data['ping_role']}>" if panel_data['ping_role'] is not None else "`None`") + "\n"
        embed.description += f"**Description:**" + (f"```\n{panel_data['description']}\n```" if panel_data['description'] is not None else "`None`") + "\n"
        embed.description += f"**Emoji:**" + (f" {panel_data['emoji']}" if panel_data['emoji'] is not None else "`None`") + "\n"
        embed.description += f"**Color:**" + (f" {panel_data['color']}" if panel_data['color'] is not None else "`None`") + "\n"
        embed.description += f"**Modal:** " + (f"\n> Type: {panel_data['modal']['type']}\n") + (f"```\n{panel_data['modal']['question']}\n```" if panel_data['modal']['question'] is not None else "`None`") + "\n"

        view = ticket_system.Panel_Edit(self.bot, panel_data, interaction.user)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()
        await view.wait()
        if view.value:
            ticket_config['panels'][name] = panel_data
            await self.bot.tickets.config.update(ticket_config)
    
    @panel.command(name="delete", description="Delete a ticket panel")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(name="Name of the panel")
    @app_commands.autocomplete(name=panel_auto_complete)
    async def delete_panel(self, interaction: discord.Interaction, name: str):
        if name == "No panels": return await interaction.response.send_message("There are no panels to delete", ephemeral=True)
        ticket_config = await self.bot.tickets.config.find(interaction.guild.id)
        if ticket_config is None:
            ticket_config = {'_id': interaction.guild.id,'category': None,'channel': None,'logging': None,'panels': {},'last_panel_message_id': None, 'transcript': None}
            await self.bot.tickets.config.insert(ticket_config)
        if name not in ticket_config['panels'].keys(): return await interaction.response.send_message("This panel does not exist", ephemeral=True, delete_after=5)
        del ticket_config['panels'][name]
        await self.bot.tickets.config.update(ticket_config)
        await interaction.response.send_message(embed=discord.Embed(description=f"Successfully deleted panel `{name}`", color=0x363940))

    @panel.command(name="edit", description="Edit a ticket panel")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(name="Name of the panel")
    @app_commands.autocomplete(name=panel_auto_complete)
    async def edit_panel(self, interaction: discord.Interaction, name: str):
        if name == "No panels": return await interaction.response.send_message("There are no panels to edit", ephemeral=True)
        ticket_config = await self.bot.tickets.config.find(interaction.guild.id)
        if ticket_config is None:
            ticket_config = {'_id': interaction.guild.id,'category': None,'channel': None,'logging': None,'panels': {},'last_panel_message_id': None, 'transcript': None}
            await self.bot.tickets.config.insert(ticket_config)
        if name not in ticket_config['panels'].keys(): return await interaction.response.send_message("This panel does not exist", ephemeral=True, delete_after=5)
        try:
            panel_data = ticket_config['panels'][name]
        except KeyError:
            return await interaction.response.send_message("This panel does not exist", ephemeral=True, delete_after=5)
        embed = discord.Embed(title=f"Settings for Panel: {name}", color=0x363940, description="")
        embed.description += f"**Support Roles:** {', '.join([f'<@&{role}>' for role in panel_data['support_roles']]) if len(panel_data['support_roles']) > 0 else '`None`'}\n"
        embed.description += f"**Ping Role:**" + (f" <@&{panel_data['ping_role']}>" if panel_data['ping_role'] is not None else "`None`") + "\n"
        embed.description += f"**Description:**" + (f"```\n{panel_data['description']}\n```" if panel_data['description'] is not None else "`None`") + "\n"
        embed.description += f"**Emoji:**" + (f" {panel_data['emoji']}" if panel_data['emoji'] is not None else "`None`") + "\n"
        embed.description += f"**Color:**" + (f" {panel_data['color']}" if panel_data['color'] is not None else "`None`") + "\n"
        embed.description += f"**Modal:**" + (f"type: {panel_data['modal']['type']}") + (f"```\n{panel_data['modal']['question']}\n```" if panel_data['modal']['question'] is not None else "`None`") + "\n"

        view = ticket_system.Panel_Edit(self.bot, panel_data, interaction.user)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()
    
    @panel.command(name="send", description="Send a ticket panel")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def send_panel(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        panel_embed = discord.Embed(title=f"{interaction.guild}'s Ticket Panel", color=0x363940)
        ticket_config = await self.bot.tickets.config.find(interaction.guild.id)
        if ticket_config is None: return await interaction.response.send_message("There are no panels to send", ephemeral=True)
        if len(ticket_config['panels'].keys()) == 0: return await interaction.response.send_message("There are no panels to send", ephemeral=True)

        panel_view = ticket_system.Panel_View()
        for panel in ticket_config['panels'].keys():
            panel = ticket_config['panels'][panel]
            panel_embed.add_field(name=panel['key'].capitalize(),value=panel['description'], inline=False)
            style = discord.ButtonStyle.gray
            if panel['color'] == "blurple": style = discord.ButtonStyle.blurple
            elif panel['color'] == "green": style = discord.ButtonStyle.green
            elif panel['color'] == "red": style = discord.ButtonStyle.red
            emoji = panel['emoji'] if panel['emoji'] is not None else None

            button = ticket_system.Panel_Button(label=panel['key'].capitalize(), style=style, emoji=emoji, custom_id=f"{ticket_config['_id']}-{panel['key']}")
            panel_view.add_item(button)

        support_channel = self.bot.get_channel(ticket_config['channel'])
        if ticket_config['last_panel_message_id'] is None:
           message = await support_channel.send(embed=panel_embed, view=panel_view)
        else:
            try:
                message = await support_channel.fetch_message(ticket_config['last_panel_message_id'])
                await message.edit(embed=panel_embed, view=panel_view)
            except discord.NotFound:
                message = await support_channel.send(embed=panel_embed, view=panel_view)
        ticket_config['last_panel_message_id'] = message.id
        await self.bot.tickets.config.update(ticket_config)

        link_view = discord.ui.View()
        link_view.add_item(discord.ui.Button(label="Panel Link", style=discord.ButtonStyle.link, url=message.jump_url))
        await interaction.followup.send(embed=discord.Embed(description="<:octane_yes:1019957051721535618> | Successfully sent the ticket panel", color=0x363940), view=link_view)

    @app_commands.command(name="add", description="Add a member to the ticket")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.describe(target="Add a member to the ticket")
    async def ticket_add(self, interaction: discord.Interaction, target: Union[discord.Role, discord.Member]):
        ticket_data = await self.bot.tickets.tickets.find(interaction.channel.id)
        if ticket_data is None: return await interaction.response.send_message("This is not a ticket channel", ephemeral=True)

        if isinstance(target, discord.Role):
            if target.id in ticket_data['roles']: return await interaction.response.send_message("This role is already added to the ticket", ephemeral=True)
            else:
                ticket_data['roles'].append(target.id)
                return await interaction.response.send_message(embed=discord.Embed(description=f"<:octane_yes:1019957051721535618> | Added {target.mention} to the ticket", color=0x363940))

        elif isinstance(target, discord.Member):
            if target.id in ticket_data['members']: return await interaction.response.send_message("This member is already added to the ticket", ephemeral=True)
            else:
                ticket_data['members'].append(target.id)

        await interaction.channel.set_permissions(target, read_messages=True, send_messages=True, view_channel=True)
        await self.bot.tickets.tickets.update(ticket_data)
        await interaction.response.send_message(embed=discord.Embed(description=f"<:octane_yes:1019957051721535618> | Added {target.mention} to the ticket", color=0x363940))
    
    @app_commands.command(name="remove", description="Remove a member from the ticket")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.describe(target="Remove a member from the ticket")
    async def ticket_remove(self, interaction: discord.Interaction, target: Union[discord.Role, discord.Member]):
        ticket_data = await self.bot.tickets.tickets.find(interaction.channel.id)
        if ticket_data is None: return await interaction.response.send_message("This is not a ticket channel", ephemeral=True)

        if isinstance(target, discord.Role):
            if target.id not in ticket_data['roles']: return await interaction.response.send_message("This role is not added to the ticket", ephemeral=True)
            else:
                ticket_data['roles'].remove(target.id)
                return await interaction.response.send_message(embed=discord.Embed(description=f"<:octane_yes:1019957051721535618> | Removed {target.mention} from the ticket", color=0x363940))

        elif isinstance(target, discord.Member):
            if target.id not in ticket_data['members']: return await interaction.response.send_message("This member is not added to the ticket", ephemeral=True)
            else:
                ticket_data['members'].remove(target.id)

        await interaction.channel.set_permissions(target, read_messages=False, send_messages=False, view_channel=False)
        ticket_data = await self.bot.tickets.tickets.find(interaction.channel.id)
        await interaction.response.send_message(embed=discord.Embed(description=f"<:octane_yes:1019957051721535618> | Removed {target.mention} from the ticket", color=0x363940))

async def setup(bot):
    await bot.add_cog(Ticket(bot))