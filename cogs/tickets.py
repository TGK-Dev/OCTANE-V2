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
    
    @app_commands.command(name="config", description="Configure ticket system")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def ticket_config(self, interaction: discord.Interaction, option: Literal['show', 'edit']):
        ticket_config = await self.bot.tickets.config.find(interaction.guild.id)
        if ticket_config is None:
            ticket_config = {'_id': interaction.guild.id,'category': None,'channel': None,'logging': None,'panels': [],'last_panel_message_id': None}
            await self.bot.tickets.config.insert(ticket_config)
        
        embed = discord.Embed(title="Ticket Config", color=0x363940)
        embed.add_field(name="Category", value=f"<#{ticket_config['category']}>" if ticket_config['category'] is not None else "None")
        embed.add_field(name="Channel", value=f"<#{ticket_config['channel']}>" if ticket_config['channel'] is not None else "None")
        embed.add_field(name="Logging", value=f"<#{ticket_config['logging']}>" if ticket_config['logging'] is not None else "None")
        embed.add_field(name="Panels", value=f"{len(ticket_config['panels'].keys())} panel(s)" if ticket_config['panels'] is not None else "None")
        embed.add_field(name="Last Panel Message ID", value=ticket_config['last_panel_message_id'] if ticket_config['last_panel_message_id'] is not None else "None")
        if option == "show":
            await interaction.response.send_message(embed=embed)
        elif option == "edit":
            view = ticket_system.Config_Edit(interaction.user, ticket_config)
            await interaction.response.send_message(embed=embed, view=view)
            view.message = await interaction.original_response()
        
    @panel.command(name="create", description="Create a ticket panel")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def create_panel(self, interaction: discord.Interaction, name: str):
        ticket_config = await self.bot.tickets.config.find(interaction.guild.id)
        if ticket_config is None:
            ticket_config = {'_id': interaction.guild.id,'category': None,'channel': None,'logging': None,'panels': {},'last_panel_message_id': None}
            await self.bot.tickets.config.insert(ticket_config)
        if name in ticket_config['panels'].keys(): return await interaction.response.send_message("This panel already exists", ephemeral=True, delete_after=5)        
        panel_data = {'key': name, 'support_roles': [], "ping_role": None, 'created_by': interaction.user.id, 'description': None, 'emoji': None, 'color': None, 'modal': {'type': 'short', 'question': "Please describe your issue"}}

        embed = discord.Embed(title=f"Settings for Panel: {name}", color=0x363940, description="")
        embed.description += f"**Support Roles:** {', '.join([f'<@&{role}>' for role in panel_data['support_roles']]) if len(panel_data['support_roles']) > 0 else '`None`'}\n"
        embed.description += f"**Ping Role:**" + (f" <@&{panel_data['ping_role']}>" if panel_data['ping_role'] is not None else "`None`") + "\n"
        embed.description += f"**Description:**" + (f"```\n{panel_data['description']}\n```" if panel_data['description'] is not None else "`None`") + "\n"
        embed.description += f"**Emoji:**" + (f" {panel_data['emoji']}" if panel_data['emoji'] is not None else "`None`") + "\n"
        embed.description += f"**Color:**" + (f" {panel_data['color']}" if panel_data['color'] is not None else "`None`") + "\n"
        embed.description += f"**Modal:** " + (f" Type: {panel_data['modal']['type']}") + (f"```\n{panel_data['modal']['question']}\n```" if panel_data['modal']['question'] is not None else "`None`") + "\n"

        view = ticket_system.Panel_Edit(self.bot, panel_data, interaction.user)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()
    
    @panel.command(name="delete", description="Delete a ticket panel")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(name="Name of the panel")
    @app_commands.autocomplete(name=panel_auto_complete)
    async def delete_panel(self, interaction: discord.Interaction, name: str):
        if name == "No panels": return await interaction.response.send_message("There are no panels to delete", ephemeral=True)
        ticket_config = await self.bot.tickets.config.find(interaction.guild.id)
        if ticket_config is None:
            ticket_config = {'_id': interaction.guild.id,'category': None,'channel': None,'logging': None,'panels': {},'last_panel_message_id': None}
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
            ticket_config = {'_id': interaction.guild.id,'category': None,'channel': None,'logging': None,'panels': {},'last_panel_message_id': None}
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