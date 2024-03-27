import discord
from discord.ext import commands
from discord import app_commands, Interaction
from .db import TicketDB, TicketConfig, Panel
from .db import Ticket as TicketData
from .view import TicketConfig_View, Panels, TicketControl, Refresh_Trancsript
from typing import List, Dict

class Ticket(commands.GroupCog, name="ticket"):
    def __init__(self, bot):
        self.bot = bot
        self.backend = TicketDB(bot)
        self.bot.tickets = self.backend

    async def PanelAutoComplete(self, interaction: Interaction, current: str) -> List[app_commands.Choice]:
        config: TicketConfig = self.backend.get_config(interaction.guild_id)
        if len(config["panels"]) == {}:
            return [app_commands.Choice(name="No panels found", value="None")]
        else:
            panels = [
                app_commands.Choice(name=panel["name"], value=panel["name"]) for panel in config["panels"].keys()
                if current.lower() in panel["name"].lower()
            ]
            return panels[:24]
    
    async def RestoreViews(self, guild: discord.Guild):
        config: TicketConfig = await self.backend.get_config(guild.id)
        view = Panels(panels=config["panels"], guild_id=guild.id)
        self.bot.add_view(view)
    
    @commands.Cog.listener()
    async def on_ready(self):
        config = await self.backend.config.get_all()
        for guild in config:
            await self.RestoreViews(self.bot.get_guild(guild["_id"]))

        self.bot.add_view(TicketControl())
        self.bot.add_view(Refresh_Trancsript())

    panel = app_commands.Group(name="panel", description="Ticket panel commands")

    @app_commands.command(name="setup", description="Setup the ticket system")
    @app_commands.default_permissions(administrator=True)
    async def setup(self, interaction: Interaction):
        embed = await self.backend.get_config_embed(interaction.guild_id)
        data = await self.backend.get_config(interaction.guild_id)
        view = TicketConfig_View(user=interaction.user, data=data)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=False)
        view.message = await interaction.original_response()

    @panel.command(name="send", description="Update/send the panel message")
    @app_commands.default_permissions(administrator=True)
    async def send(self, interaction: Interaction):
        await interaction.response.send_message("Please wait while I update the panel message", ephemeral=True)
        config: TicketConfig = await self.backend.get_config(interaction.guild_id)
        panels_channels = {config["default_channel"]: []}
        panels: Dict[str, Panel] = config["panels"]

        for name, panel in panels.items():
            if panel['channel'] != None:    
                if panel['channel'] not in panels_channels:
                    panels_channels[panel['channel']] = []
                panels_channels[panel['channel']].append(config["panels"][name])
            else:
                panels_channels[config["default_channel"]].append(config["panels"][name])

        for channel, panels in panels_channels.items():
            channel = interaction.guild.get_channel(channel)
            panel_message = None

            embed = discord.Embed(color=interaction.client.default_color)
            embed.set_author(name=f"{interaction.guild.name} Ticket System", icon_url=interaction.guild.icon.url)
            
            for panel in panels:
                panel: Panel = panel
                if panel['panel_message'] != None and panel_message == None:
                    
                    try:
                        panel_message = await channel.fetch_message(panel['panel_message'])
                    except discord.NotFound:
                        panel_message = None
                    
                embed.add_field(name=panel['name'], value=panel['description'], inline=False)

            view = Panels(panels=panels_channels[channel.id], guild_id=interaction.guild_id)
            self.bot.add_view(view)

            if panel_message == None and len(panels) > 0:                
                panel_message = await channel.send(embed=embed, view=view)
                config["panels"][panel['name']]['panel_message'] = panel_message.id

            elif isinstance(panel_message, discord.Message):
                await panel_message.edit(embed=embed, view=view)

        await self.backend.update_config(interaction.guild_id, config)
        await interaction.edit_original_response(content="Panel message updated")

    @commands.hybrid_command(name="add", description="Add a Roles/Users to the ticket")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.describe(target="Role/User to add")
    async def _add(self, ctx: commands.Context, target: discord.Role | discord.Member):
        ticket_data: TicketData = await self.backend.ticket.find(ctx.channel.id)
        if not ticket_data:
            return await ctx.send("This is not a ticket channel", ephemeral=True)
        
        if isinstance(target, discord.Role):
            if target.id in ticket_data["added_roles"]:
                return await ctx.send(embed=discord.Embed(description=f"The role {target.mention} already part of the ticket", color=self.bot.default_color), ephemeral=True)
            ticket_data["added_roles"].append(target.id)
        elif isinstance(target, discord.Member):
            if target.id in ticket_data["added_users"]:
                return await ctx.send(embed=discord.Embed(description=f"The user {target.mention} is already part of the ticket", color=self.bot.default_color), ephemeral=True)
            ticket_data["added_users"].append(target.id)

        overwrites = discord.PermissionOverwrite(view_channel=True)
        await ctx.channel.set_permissions(target, overwrite=overwrites)
        await self.backend.ticket.update(ticket_data)
        await ctx.send(embed=discord.Embed(description=f"{target.mention} has been added to the ticket", color=self.bot.default_color))
    
    @commands.hybrid_command(name="remove", description="Remove a Roles/Users from the ticket")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.describe(target="Role/User to remove")
    async def _remove(self, ctx: commands.Context, target: discord.Role | discord.Member):
        ticket_data: TicketData = await self.backend.ticket.find(ctx.channel.id)
        if not ticket_data:
            return await ctx.send("This is not a ticket channel", ephemeral=True)
        
        try:
            if isinstance(target, discord.Role):            
                ticket_data["added_roles"].remove(target.id)
            elif isinstance(target, discord.Member):
                ticket_data["added_users"].remove(target.id)
        except ValueError:
            pass
        
        overwrites = discord.PermissionOverwrite(view_channel=False)
        await ctx.channel.set_permissions(target, overwrite=overwrites)
        await self.backend.ticket.update(ticket_data)
        await ctx.send(embed=discord.Embed(description=f"{target.mention} has been removed from the ticket", color=self.bot.default_color))


async def setup(bot):
    await bot.add_cog(Ticket(bot))