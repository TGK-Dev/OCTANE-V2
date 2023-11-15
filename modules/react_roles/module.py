import discord
from discord.ext import commands
from discord import app_commands
from utils.db import Document
from .view import RoleMenu_Panel, RoleMenu_Perent
from utils.paginator import Paginator
from .db import Backend, RoleMenu, RoleMenuProfile, ReactRoleMenuType, RoleMenuRoles
from typing import List
from utils.transformer import TimeConverter


class RoleMenus(commands.GroupCog, name="role_menus", description="Role menus"):
    def __init__(self, bot):
        self.bot = bot
        self.backend = Backend(self.bot)
        self.bot.rm = self.backend
    
    async def profile_auto(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        guild_config = await self.backend.get_config(interaction.guild_id)
        choices = [
            app_commands.Choice(name=profile['name'], value=profile['name']) 
            for profile in guild_config['roles'].values()
        ]
        return choices[:24]
        

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.wait_until_ready()
        await self.backend.load()
        for key, value in self.backend.Cach.items():
            for profile in value['roles'].values():
                profile = RoleMenuProfile(**profile)
                viewb = RoleMenu_Perent(profile, self.bot.get_guild(key), _type="button")
                viewd = RoleMenu_Perent(profile, self.bot.get_guild(key), _type="dropdown")
                self.bot.add_view(viewb)
                self.bot.add_view(viewd)
        print("Loaded role menus")
    
    @app_commands.command(name="create", description="Create a role menu")
    async def create(self, interaction: discord.Interaction, display_name: str):
        config: RoleMenu = await self.backend.get_config(interaction.guild_id)
        if display_name in config["roles"].keys():
            await interaction.response.send_message("A role menu with that name already exists", ephemeral=True)
            return
        if len(config["roles"]) >= config["max_profiles"]:
            await interaction.response.send_message("You have reached the max amount of profiles", ephemeral=True)
            return
        
        profile = RoleMenuProfile(
            name=display_name,
            display_name=display_name,
            req_roles=[],
            bl_roles=[],
            type=ReactRoleMenuType.ADD_AND_REMOVE.value,
            roles={}
        )

        embed = discord.Embed(title=f"Creating New Role Menu {display_name}", description="", color=interaction.client.default_color)
        embed.add_field(name="Display Name", value=f"<:nat_reply:1146498277068517386> {profile['display_name']}", inline=True)
        embed.add_field(name="Required Role", value="`None`", inline=True)
        embed.add_field(name="Blacklisted Role", value="`None`", inline=True)
        embed.add_field(name="Type", value=str(ReactRoleMenuType(profile["type"])), inline=True)
        embed.add_field(name="Roles", value="* No roles", inline=True)
        
        view = RoleMenu_Panel(interaction.user, interaction.guild, profile)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=False)
        view.message = await interaction.original_response()
    
    @app_commands.command(name="edit", description="Edit a role menu")
    @app_commands.autocomplete(profile=profile_auto)
    async def edit(self, interaction: discord.Interaction, profile: str):
        data = await self.backend.get_profile(interaction.guild_id, profile)
        if data is None:
            await interaction.response.send_message("That profile does not exist", ephemeral=True)
            return
        profile = RoleMenuProfile(**data)
        embed = discord.Embed(title=f"Editing Role Menu {profile['display_name']}", description="", color=interaction.client.default_color)
        
        req_role = []
        for data in profile['req_roles']:
            role = interaction.guild.get_role(data)
            if role:
                req_role.append(role.mention)
            else:
                profile['req_roles'].remove(data)
        req_role = ", ".join(req_role) if req_role else "`None`"

        bl_role = []
        for data in profile['bl_roles']:
            role = interaction.guild.get_role(data)
            if role:
                bl_role.append(role.mention)
            else:
                profile['bl_roles'].remove(data)
        bl_role = ", ".join(bl_role) if bl_role else "`None`"

        roles = ""
        for data in profile['roles'].values(): 
            role = interaction.guild.get_role(data['role_id'])
            if not role:
                del profile['roles'][data['role_id']]
                continue
            roles += f"{data['emoji']}: {role.mention}\n"
        embed.add_field(name="Display Name", value=f"<:nat_reply:1146498277068517386> {profile['display_name']}", inline=False)
        embed.add_field(name="Required Role", value=f"<:nat_reply:1146498277068517386> {req_role}", inline=False)
        embed.add_field(name="Blacklisted Role", value=f"<:nat_reply:1146498277068517386> {bl_role}", inline=False)
        embed.add_field(name="Type", value=f"<:nat_reply:1146498277068517386> {str(ReactRoleMenuType(profile['type']))}", inline=False)
        embed.add_field(name="Roles", value=roles, inline=False)

        view = RoleMenu_Panel(interaction.user, interaction.guild, profile)
        await interaction.response.send_message(embed=embed, ephemeral=False, view=view)
        view.message = await interaction.original_response()
    
    @app_commands.command(name="delete", description="Delete a role menu")
    @app_commands.autocomplete(profile=profile_auto)
    @app_commands.describe(profile="The profile to delete")
    async def delete(self, interaction: discord.Interaction, profile: str):
        data = await self.backend.get_profile(interaction.guild_id, profile)
        if data is None:
            await interaction.response.send_message("That profile does not exist", ephemeral=True)
            return
        await self.backend.delete_profile(interaction.guild_id, profile['name'])
        await interaction.response.send_message(f"Deleted profile {profile['display_name']}", ephemeral=True)
    
    @app_commands.command(name="list", description="List all role menus")
    async def _list(self, interaction: discord.Interaction):
        data = await self.backend.get_profile(interaction.guild_id)

        if data is None:
            await interaction.response.send_message("There are no profiles", ephemeral=True)
        pages = []
        for menu in data.values():
            embed = discord.Embed(title=f"Role Menu {menu['display_name']}", description="", color=interaction.client.default_color)
            embed.description += "* **DisplayName**: " + menu['display_name'] + "\n"
            embed.description += "* **Type**: " + str(ReactRoleMenuType(menu['type'])) + "\n"
            req_role = []
            for data in menu['req_roles']:
                role = interaction.guild.get_role(data)
                if role:
                    req_role.append(role.mention)
                else:
                    menu['req_roles'].remove(data)
            req_role = ", ".join(req_role) if req_role else "`None`"
            bl_role = []
            for data in menu['bl_roles']:
                role = interaction.guild.get_role(data)
                if role:
                    bl_role.append(role.mention)
                else:
                    menu['bl_roles'].remove(data)
            bl_role = ", ".join(bl_role) if bl_role else "`None`"
            embed.description += "* **Required Role**: " + req_role + "\n"
            embed.description += "* **Blacklisted Role**: " + bl_role + "\n"
            menu_roles = ""

            for entery in menu['roles']:
                role = interaction.guild.get_role(menu['roles'][entery]['role_id'])
                if role:
                    menu_roles += f"{role.mention}: {menu['roles'][entery]['emoji']}\n"
            embed.description += "* **Roles**: " + menu_roles + "\n"
            pages.append(embed)

        await Paginator(interaction, pages).start(embeded=True, quick_navigation=False)

            
    @app_commands.command(name="send", description="Send a role menu")
    @app_commands.autocomplete(profile=profile_auto)
    @app_commands.describe(profile="The profile to send", timeout="How long the menu should be active for", embed="The embed format", _type="The interaction type of the menu (button or dropdown)")
    @app_commands.choices(
        embed=[
        app_commands.Choice(name="big", value="big"),
        app_commands.Choice(name="small", value="small")
        ],
        _type=[
            app_commands.Choice(name="button", value="button"),
            app_commands.Choice(name="dropdown", value="dropdown")
        ]

    )
    @app_commands.rename(embed="embed_format")
    async def send(self, interaction: discord.Interaction, profile: str, timeout: app_commands.Transform[int, TimeConverter]=None, embed: str="big", _type: str="button"):
        data = await self.backend.get_profile(interaction.guild_id, profile)
        if data is None:
            await interaction.response.send_message("That profile does not exist", ephemeral=True)
            return
        profile = RoleMenuProfile(**data)        
        match embed:
            case "big":
                view = RoleMenu_Perent(data, interaction.guild, timeout, labled=False, _type=_type)
                embed: discord.Embed = discord.Embed(title=profile['display_name'], description="",color=interaction.client.default_color)
                embed.description += f"Press the below buttons to interact with menu\n"
                embed.set_footer(text=f"Menu type: {str(ReactRoleMenuType(profile['type']))}")
                for role in data['roles']:
                    embed.description += f"###  {data['roles'][role]['emoji']} : {interaction.guild.get_role(data['roles'][role]['role_id']).mention}\n"
            case "small":
                embed = discord.Embed(title=profile['display_name'], description="",color=interaction.client.default_color)
                view = RoleMenu_Perent(data, interaction.guild, timeout, labled=True, _type=_type)
        await interaction.response.send_message("Sent Successfully", ephemeral=True)
        await interaction.channel.send(embed=embed, view=view)
        if timeout is not None:
            view.message = await interaction.original_response()
        self.bot.add_view(view)

async def setup(bot):
    await bot.add_cog(RoleMenus(bot))





