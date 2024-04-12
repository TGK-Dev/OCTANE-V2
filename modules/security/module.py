import discord
from discord import app_commands
from discord.ext import commands
from .db import GuildConfig, Backend, ActionType, PunishmentType, ActionOn
from typing import List, Literal

from utils.views.selects import Mention_select

@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
class Security(commands.GroupCog):
    def __init__(self, bot):
        self.bot = bot
        self.backend = Backend(bot)
    
    @commands.Cog.listener()
    async def on_ready(self):
        if await self.backend.setup() == None:
            user: discord.User = self.bot.get_user(488614633670967307)
            await user.send("The Security Module has not been setup. Please run the `/setup` command to setup the module.")
                
        

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id in self.bot.owner_ids: return True
        if interaction.user.id in self.backend.config['owners']: return True
        else:
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return False

    @commands.Cog.listener()
    async def on_audit_log_entry_create(self, entry: discord.AuditLogEntry):
        match entry.action:

            case discord.AuditLogAction.channel_create:
                pass
            case discord.AuditLogAction.channel_update:
                pass
            case discord.AuditLogAction.channel_delete:
                pass
            case discord.AuditLogAction.role_create:
                pass
            case discord.AuditLogAction.role_update:
                pass
            case discord.AuditLogAction.role_delete:
                pass
            case discord.AuditLogAction.guild_update:
                pass
            case discord.AuditLogAction.bot_add:
                pass
            case discord.AuditLogAction.webhook_create:
                pass
            case discord.AuditLogAction.webhook_update:
                pass
            case discord.AuditLogAction.webhook_delete:
                pass


    @commands.Cog.listener()
    async def on_channel_create(self, user: discord.Member | discord.User, guild: discord.Guild, channel: discord.TextChannel | discord.VoiceChannel | discord.CategoryChannel | discord.ForumChannel):
        if user.id in self.backend.config['owners']: return
        if user.id == self.bot.user.id: return
        
        if user.id in self.backend.config['channel']['whitelistUsers']: return

        userRoles: List[int] = [role.id for role in user.roles]

        if not (set(userRoles) & set(self.backend.config['channel']['whitelistRoles'])): return

        await self.backend.punish(guild=guild, user=user, Moderator=guild.me, 
            punishment=self.backend.config['channel']['Punismhment']['create'], target=channel)
        await channel.delete(reason="Channel Created by Unauthorized User")
    
    @app_commands.command(name="setup", description="Setup the Security Module")
    async def _setup(self, interaction: discord.Interaction):
        await interaction.response.send_message("Setting up the Security Module...", ephemeral=True)

        config = await self.backend.dbconfig.find(interaction.client.user.id)
        if not config:
            config: GuildConfig = {
                '_id': interaction.client.user.id,
                'guildID': interaction.guild.id,
                'owners': [interaction.guild.owner_id],
                'quarantineRole': None,
                'log_channel': None,
                'channel': {
                    'whitelistRoles': [],
                    'whitelistUsers': [],
                    'Punishment': {
                        'edit': None,
                        'delete': None,
                        'create': None,
                    }
                },
                'role': {
                    'whitelistRoles': [],
                    'whitelistUsers': [],
                    'Punishment': {
                        'edit': None,
                        'delete': None,
                        'create': None,
                    }
                },
                'webhook': {
                    'whitelistRoles': [],
                    'whitelistUsers': [],
                    'Punishment': {
                        'edit': None,
                        'delete': None,
                        'create': None,
                    }
                }
            }
            quarantineRole = discord.utils.get(interaction.guild.roles, name="Quarantine")

            await interaction.edit_original_response(content="Setting up Quarantine Role...")

            if not quarantineRole:
                quarantineRole = await interaction.guild.create_role(name="Quarantine", reason="Setting up the Security Module")
                await quarantineRole.edit(position=interaction.guild.me.top_role.position - 1)

            config['quarantineRole'] = quarantineRole.id
            await self.backend.dbconfig.upsert(config)
            for channel in interaction.guild.channels:
                await channel.set_permissions(quarantineRole, view_channel=False, send_messages=False, read_message_history=False, connect=False, speak=False, reason="Setting up the Security Module")

        await interaction.edit_original_response(content="The Security Module has been setup.")

    @app_commands.command(name="whitelist", description="Whitelist a User or Role")
    async def _whitelist(self, interaction: discord.Interaction, action: ActionType, on: ActionOn):
        view = discord.ui.View()
        view.value = None
        view.select = Mention_select(placeholder="Select Users or Roles Which you want to add/remove from Whitelist", min_values=1, max_values=10)
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True)

        await view.wait()

        if view.value is None or view.value is False: await interaction.delete_original_response()

        await view.select.interaction.response.edit_message(content="Processing...", view=None)

        config: GuildConfig = self.backend.config

        values = view.select.values
        updates = {
            'roles': {'add': [], 'remove': []},
            'users': {'add': [], 'remove': []}
        }
        for value in values:
            if isinstance(value, discord.Role):
                if value.id in config[on.name.lower()]['whitelistRoles']:
                    updates['roles']['remove'].append(value.id)
                    config[on.name.lower()]['whitelistRoles'].remove(value.id)
                else:
                    updates['roles']['add'].append(value.id)
                    config[on.name.lower()]['whitelistRoles'].append(value.id)
            elif isinstance(value, discord.Member):
                if value.id in config[on.name.lower()]['whitelistUsers']:
                    updates['users']['remove'].append(value.id)
                    config[on.name.lower()]['whitelistUsers'].remove(value.id)
                else:
                    updates['users']['add'].append(value.id)
                    config[on.name.lower()]['whitelistUsers'].append(value.id)
        
        await self.backend.dbconfig.upsert(config)

        embed = discord.Embed(description="Whitelist Updated\n\n", color=self.bot.default_color)
        embed.description += f"Roles:\n> Added: {', '.join([f'<@&{role}>' for role in updates['roles']['add']])}\n> Removed: {', '.join([f'<@&{role}>' for role in updates['roles']['remove']])}\n\n"
        embed.description += f"Users:\n> Added: {', '.join([f'<@{user}>' for user in updates['users']['add']])}\n> Removed: {', '.join([f'<@{user}>' for user in updates['users']['remove']])}"

        await view.select.interaction.edit_original_response(embed=embed)



async def setup(bot):
    await bot.add_cog(Security(bot))

