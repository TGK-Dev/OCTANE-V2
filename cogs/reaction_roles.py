import discord
from discord.ext import commands
from discord import app_commands
from utils.db import Document
from utils.views.reaction_role_system import ReactionRoleMenu, Reaction_Role_View, RoleMenu_Button
from utils.paginator import Paginator
from typing import List

class ReactionRolesDB():
    def __init__(self, bot, Document):
        self.bot = bot
        self.reaction_roles = Document(bot.db, "reaction_roles")

    async def get_config(self, guild_id):
        config = await self.reaction_roles.find(guild_id)
        if config is None: config = await self.create_config(guild_id)
        return config

    async def create_config(self, guild_id):
        config = {"_id": guild_id,"menues": {},"limit": 5}
        await self.reaction_roles.insert(config)
        return config

    async def get_all(self):
        return await self.reaction_roles.get_all()

    async def update_config(self, guild_id, data):
        await self.reaction_roles.update(guild_id, data)

class ReactionRoles(commands.GroupCog, name="reactroles", description="Manage Reacion roles munes"):
    def __init__(self, bot):
        self.bot = bot
        self.bot.rr = ReactionRolesDB(bot, Document)
    
    async def menu_auto_complete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        guild_config = await self.bot.rr.get_config(interaction.guild_id)
        return [
            app_commands.Choice(name=menu_name, value=menu_name)
            for menu_name in guild_config["menues"].keys() if current.lower() in menu_name.lower()
        ]

    @commands.Cog.listener()
    async def on_ready(self):
        reaction_data = await self.bot.rr.get_all()
        for guild_config in reaction_data:
            guild = self.bot.get_guild(guild_config['_id'])
            if guild is None: continue
            for menu_data in guild_config['menues'].keys():
                menu_data = guild_config['menues'][menu_data]
                if len(menu_data['roles']) == 0: continue
                view = Reaction_Role_View(menu_data, guild)
                self.bot.add_view(view)
    
    @app_commands.command(name="create", description="Create a reaction role menu")
    @app_commands.describe(name="Name of the menu")
    @app_commands.default_permissions(manage_guild=True)
    async def create(self, interaction: discord.Interaction, name:str):
        guild_config = await self.bot.rr.get_config(interaction.guild_id)
        if len(guild_config["menues"]) >= guild_config["limit"]: return await interaction.response.send_message("You have reached the limit of reaction role menues", ephemeral=True)
        if name in guild_config['menues'].keys(): await interaction.response.send_message("A menu with that name already exists", ephemeral=True)
        menu_data = {'name': name, 'roles': [], 'required_roles': [], 'display_name': None,'type': None}
        embed = discord.Embed(description="", color=0x363940)
        embed.description += f"**Name:** {name}\n"
        embed.description += f"**Display Name:** {menu_data['display_name'] if menu_data['display_name'] else '`None`'}\n"
        embed.description += f"**Roles:** {', '.join([f'<@&{role}>' for role in menu_data['roles']]) if menu_data['roles'] else '`None`'}\n"
        embed.description += f"**Required Roles:** {','.join([f'<@&{role}>' for role in menu_data['required_roles']]) if menu_data['required_roles'] else '`None`'}\n"
        embed.description += f"**Type:** {menu_data['type'] if menu_data['type'] else '`None`'}\n"
        view = ReactionRoleMenu(menu_data, interaction=interaction)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()
        await view.wait()

        if view.value:
            guild_config['menues'][name] = menu_data
            await self.bot.rr.update_config(interaction.guild_id, guild_config)
    
    @app_commands.command(name="delete", description="Delete a reaction role menu")
    @app_commands.describe(name="Name of the menu")
    @app_commands.default_permissions(manage_guild=True)
    async def delete(self, interaction: discord.Interaction, name:str):
        guild_config = await self.bot.rr.get_config(interaction.guild_id)
        if name not in guild_config['menues'].keys(): await interaction.response.send_message("That menu does not exist", ephemeral=True)
        for view in self.bot.persistent_views:
            try:
                if view._id == f"{interaction.guild.id}:menu:{guild_config['menues'][name]['name']}":
                    view.stop()
                    break
            except AttributeError: pass
            except Exception as e: raise e
        del guild_config['menues'][name]
        await self.bot.rr.update_config(interaction.guild_id, guild_config)
        await interaction.response.send_message("Menu deleted", ephemeral=True)
    
    @app_commands.command(name="list", description="List all reaction role menues")
    @app_commands.default_permissions(manage_guild=True)
    async def list(self, interaction: discord.Interaction):
        guild_config = await self.bot.rr.get_config(interaction.guild_id)
        if not guild_config['menues']: await interaction.response.send_message("There are no reaction role menues", ephemeral=True)
        embeds = []
        for name, menu_data in guild_config['menues'].items():
            embed = discord.Embed(description="", color=0x363940)
            embed.description += f"**Name:** {name}\n"
            embed.description += f"**Display Name:** {menu_data['display_name'] if menu_data['display_name'] else '`None`'}\n"
            embed.description += f"**Roles:** {', '.join([f'<@&{role}>' for role in menu_data['roles']]) if menu_data['roles'] else '`None`'}\n"
            _type = '`Add & Remove`' if menu_data['type'] == 'add_remove' else '`Add Only`' if menu_data['type'] == 'add_only' else '`Remove Only`' if menu_data['type'] == 'remove_only' else '`None`'
            embed.description += f"**Required Roles:** {','.join([f'<@&{role}>' for role in menu_data['required_roles']]) if menu_data['required_roles'] else '`None`'}\n"
            embed.description += f"**Type:** {_type}\n"
            embeds.append(embed)
        await Paginator(interaction, embeds).start(embeded=True, quick_navigation=False)
    
    @app_commands.command(name="send", description="Send a reaction role menu")
    @app_commands.describe(name="Name of the menu", channel="Channel to send the menu in")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.autocomplete(name=menu_auto_complete)
    async def send(self, interaction: discord.Interaction, name:str, channel:discord.TextChannel=None):
        guild_config = await self.bot.rr.get_config(interaction.guild_id)
        if name not in guild_config['menues'].keys(): await interaction.response.send_message("That menu does not exist", ephemeral=True)
        menu = guild_config['menues'][name]
        embed = discord.Embed(title=f"", color=0x363940)
        embed.title += f"{menu['display_name'] if menu['display_name'] else name}\n"
        view = Reaction_Role_View(menu, guild=interaction.guild)
        channel = channel if channel != None else interaction.channel
        await interaction.response.send_message("Menu sent", ephemeral=True)
        await channel.send(embed=embed, view=view)        

async def setup(bot):
    await bot.add_cog(ReactionRoles(bot))