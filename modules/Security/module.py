import discord
from discord import app_commands, Interaction
from discord.ext import commands
from .db import *


class Security(commands.GroupCog):
    def __init__(self, bot):
        self.bot = bot
        self.backend = Backend(bot)

    @commands.Cog.listener()
    async def on_ready(self):
        guild = self.bot.get_guild(1042419983608729632)

    @commands.command(name="hot")
    async def _hot(self, ctx):
        await self.bot.reload_extension('modules.Security.module')
        await ctx.send("Done")

    @commands.command(name="unban")
    async def _unban(self, ctx):
        user = await self.bot.fetch_user(1048280982039572500)
        await ctx.guild.unban(user)
        await ctx.send("Done")

    @commands.command(name="ad")
    async def _ad(self, ctx):
        role = ctx.guild.get_role(1147788215936360458)
        await ctx.author.add_roles(role)
        await ctx.send("Done")

    @commands.Cog.listener()
    async def on_audit_log_entry_create(self, entry: discord.AuditLogEntry):
        if entry.user.id == self.bot.user.id:
            return
        match entry.action:
            case discord.AuditLogAction.channel_create:
                punished = await self.check_channel_create(user=entry.user, guild=entry.guild, channel=entry.target)
                if not punished and entry.user.id != self.bot.user.id:
                    await self.backend.check_channel_create_history(entry)

            case discord.AuditLogAction.channel_delete:
                punished = await self.check_channel_delete(user=entry.user, guild=entry.guild, channel=entry.target)
                if not punished and entry.user.id != self.bot.user.id:
                    await self.backend.check_channel_delete_history(entry)

            case discord.AuditLogAction.channel_update:
                await self.check_channel_update(entry)
            case discord.AuditLogAction.role_create:
                await self.check_role_create(user=entry.user, guild=entry.guild, role=entry.target)
            case discord.AuditLogAction.role_delete:
                await self.check_role_delete(user=entry.user, guild=entry.guild, role=entry.target)
            case discord.AuditLogAction.role_update:
                await self.check_role_update(entry=entry)
            case discord.AuditLogAction.member_role_update:
                pass            
            case discord.AuditLogAction.bot_add:
                await self.check_bot_add(entry=entry)

            case _:
                pass

    #NOTE: Start of the functions that check for security for channel creation, deletion, and editing
    
    async def check_channel_create(self, user: discord.Member | discord.User, guild: discord.Guild, channel: discord.TextChannel | discord.ForumChannel) -> bool:
        config: Config = await self.backend.get_config(guild.id)
        whitelisted = None

        if (user.id in config['channel']['Create']['whitelist']['users'] or user.id in
                config['owners'] or user.id == self.bot.user.id):
            whitelisted = True
        else:
            whitelisted = False

        if whitelisted is False or whitelisted is None:

            user_roles = [role.id for role in user.roles]
            if not (set(user_roles) & set(config['channel']['Create']['whitelist']['roles'])):
                whitelisted = False
            else:
                whitelisted = True

        if whitelisted is False or whitelisted is None:
            punishment = Punishment(config['channel']['Create']['punishment'])
            await self.backend.do_punishment(guild=guild, user=user, punishment=punishment,
                                             reason="Unauthorised channel creation")
            await channel.delete(reason="Unauthorised channel creation")
            return True
        else:
            
            quaratine_role = guild.get_role(config['quarantine_role'])
            if quaratine_role is None:
                try:
                    await guild.owner.send("Quarantine role not found, I have created one for you please check it later")
                except:
                    pass
                await self.backend.set_quarantine_role(guild=guild)
            else:
                await channel.set_permissions(quaratine_role, send_messages=False, view_channel=False)

            return False
        

    async def check_channel_delete(self, user: discord.Member | discord.User, guild: discord.Guild, channel: discord.TextChannel | discord.ForumChannel) -> bool:
        config: Config = await self.backend.get_config(guild.id)
        whitelisted = None
        if (user.id in config['channel']['Delete']['whitelist']['users'] or user.id in
                config['owners'] or user.id == self.bot.user.id):
            whitelisted = True
        else:
            whitelisted = False

        if whitelisted is False or whitelisted is None:
            user_roles = [role.id for role in user.roles]
            if not (set(user_roles) & set(config['channel']['Delete']['whitelist']['roles'])):
                whitelisted = False
            else:
                whitelisted = True

        if whitelisted is False or whitelisted is None:
            punishment = Punishment(config['channel']['Delete']['punishment'])
            await self.backend.do_punishment(guild=guild, user=user, punishment=punishment,
                                             reason="Unauthorised channel deletion")
            return True
        else:
            return False

    async def check_channel_update(self, entry: discord.AuditLogEntry) -> bool:
        user = entry.user
        guild = entry.guild
        channel = entry.target
        changes = entry.changes

        config: Config = await self.backend.get_config(guild.id)
        whitelisted = None
        if (user.id in config['channel']['Edit']['whitelist']['users'] or user.id in
                config['owners'] or user.id == self.bot.user.id):
            whitelisted = True
        else:
            whitelisted = False

        if whitelisted is False or whitelisted is None:
            user_roles = [role.id for role in user.roles]
            if not (set(user_roles) & set(config['channel']['Edit']['whitelist']['roles'])):
                whitelisted = False
            else:
                whitelisted = True

        if whitelisted is False or whitelisted is None:
            punishment = Punishment(config['channel']['Edit']['punishment'])
            await self.backend.do_punishment(guild=guild, user=user, punishment=punishment,
                                             reason="Unauthorised channel edit")
            await channel.edit(**changes.before.__dict__)
            return True
        else:
            
            quaratine_role = guild.get_role(config['quarantine_role'])
            if quaratine_role is None:
                await guild.owner.send("Quarantine role not found, I have created one for you please check it later")
                quaratine_role = await self.backend.set_quarantine_role(guild=guild)
            
            await channel.set_permissions(quaratine_role, send_messages=False, view_channel=False)

            return False

    #NOTE: Start of the functions that check for security for role creation, deletion, and editing

    async def check_role_create(self, user: discord.Member | discord.User, guild: discord.Guild, role: discord.Role) -> bool:
        config: Config = await self.backend.get_config(guild.id)
        whitelisted = None
        if (user.id in config['role']['Create']['whitelist']['users'] or user.id in
                config['owners'] or user.id == self.bot.user.id):
            whitelisted = True
        else:
            whitelisted = False

        if whitelisted is False or whitelisted is None:
            user_roles = [role.id for role in user.roles]
            if not (set(user_roles) & set(config['role']['Create']['whitelist']['roles'])):
                whitelisted = False
            else:
                whitelisted = True

        if whitelisted is False or whitelisted is None:
            punishment = Punishment(config['role']['Create']['punishment'])
            await self.backend.do_punishment(guild=guild, user=user, punishment=punishment,
                                             reason="Unauthorised role creation")
            
            await role.delete(reason="Unauthorised role creation")
            return True
        else:
            return False

    async def check_role_delete(self, user: discord.Member | discord.User, guild: discord.Guild, role: discord.Role) -> bool:
        config: Config = await self.backend.get_config(guild.id)
        whitelisted = None
        if (user.id in config['role']['Delete']['whitelist']['users'] or user.id in
                config['owners'] or user.id == self.bot.user.id):
            whitelisted = True
        else:
            whitelisted = False

        if whitelisted is False or whitelisted is None:
            user_roles = [role.id for role in user.roles]
            if not (set(user_roles) & set(config['role']['Delete']['whitelist']['roles'])):
                whitelisted = False
            else:
                whitelisted = True

        if whitelisted is False or whitelisted is None:
            punishment = Punishment(config['role']['Delete']['punishment'])
            await self.backend.do_punishment(guild=guild, user=user, punishment=punishment,
                                             reason="Unauthorised role deletion")
            return True
        else:
            return False
    
    async def check_role_update(self, entry: discord.AuditLogEntry) -> bool:
        user = entry.user
        guild = entry.guild
        role = entry.target
        before = entry.before
        after = entry.after

        config: Config = await self.backend.get_config(guild.id)
        whitelisted = None
        if (user.id in config['role']['Edit']['whitelist']['users'] or user.id in
                config['owners'] or user.id == self.bot.user.id):
            whitelisted = True
        else:
            whitelisted = False

        if whitelisted is False or whitelisted is None:
            user_roles = [role.id for role in user.roles]
            if not (set(user_roles) & set(config['role']['Edit']['whitelist']['roles'])):
                whitelisted = False
            else:
                whitelisted = True

        if whitelisted is False or whitelisted is None:
            punishment = Punishment(config['role']['Edit']['punishment'])
            await self.backend.do_punishment(guild=guild, user=user, punishment=punishment,
                                             reason="Unauthorised role edit")
            await role.edit(**before.__dict__)
            
            return True
        else:
            return False

    #NOTE: Start of the functions that check for security for bot addition

    async def check_bot_add(self, entry: discord.AuditLogEntry):
        target= entry.target
        user = entry.user
        guild = entry.guild

        if target.bot:
            if not target.public_flags.verified_bot:
                await guild.kick(target, reason="Unverified bot")
                await self.backend.do_punishment(guild=guild, user=user, punishment=Punishment.Quarantine,
                                             reason="Unverified bot")
                await self.backend.do_punishment(guild=guild, user=target, punishment=Punishment.Ban, reason="Unverified bot")



    @app_commands.command(name="quarantine", description="Quarantine a user")
    @app_commands.default_permissions(administrator=True)
    async def _quarantine(self, interaction: Interaction, user: discord.Member, reason: str = "No reason provided"):
        await interaction.response.defer()
        await self.backend.do_punishment(guild=interaction.guild, user=user, punishment=Punishment.Quarantine,
                                         reason=reason)
        embed = discord.Embed(description=f"Quarantined {user.mention} | `{user.id}`", color=self.bot.default_color)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="unquarantine", description="Unquarantine a user")
    @app_commands.default_permissions(administrator=True)
    async def _unquarantine(self, interaction: Interaction, user: discord.Member, reason: str = "No reason provided"):
        await interaction.response.defer()
        data = await self.backend.quarantine.find(interaction.guild.id)
        if isinstance(data, dict):
            await self.backend.unquarantineUser(interaction.guild, user, data, reason)




async def setup(bot):
    await bot.add_cog(Security(bot))
