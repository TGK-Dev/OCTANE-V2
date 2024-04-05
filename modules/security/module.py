import discord
from discord import app_commands
from discord.ext import commands
from .db import GuildConfig, Backend
from typing import List

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
    async def on_channel_create(self, user: discord.Member | discord.User, guild: discord.Guild, channenl: discord.TextChannel | discord.VoiceChannel | discord.CategoryChannel | discord.ForumChannel):
        if user.id in self.backend.config['owners']: return
        if user.id == self.bot.user.id: return
        
        if user.id in self.backend.config['channel']['whitelistUsers']: return

        userRoles: List[int] = [role.id for role in user.roles]

        if not (set(userRoles) & set(self.backend.config['channel']['whitelistRoles'])): return

        await self.backend.punish()
    
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
                await quarantineRole.role.edit(position=interaction.guild.me.top_role.position - 1)
            config['quarantineRole'] = quarantineRole.id
            for channel in interaction.guild.channels:
                await channel.set_permissions(quarantineRole, view_channel=False, send_messages=False, read_message_history=False, connect=False, speak=False, reason="Setting up the Security Module")

        await interaction.response.send_message("The Security Module has been setup.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Security(bot))

