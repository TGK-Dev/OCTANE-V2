import discord
import datetime
from utils.db import Document
from utils.embed import get_formated_embed, get_formated_field
from typing import TypedDict, List
from enum import Enum

class PunishmentType(Enum):
    KICK = 1
    BAN = 2
    TIMEOUT = 3
    Quarantine = 4

class Quarantine(TypedDict):
    _id: int
    user_id: int
    guild_id: int
    quarantine_by: int
    reason: str
    roles: List[int]    

class Punishment(TypedDict):
    edit: PunishmentType
    delete: PunishmentType
    create: PunishmentType

class SubConfig(TypedDict):
    whitelistRoles: List[int]
    whitelistUsers: List[int]
    Punismhment: Punishment

class GuildConfig(TypedDict):
    _id: int
    guildID: int
    owners: List[int]
    quarantineRole: int
    log_channel: int
    channel: SubConfig
    role: SubConfig
    webhook: SubConfig

class Backend:
    def __init__(self, bot):
        self.db = bot.mongo['Security']
        self.bot = bot
        self.dbconfig = Document(self.db, 'config')
        self.config: GuildConfig = None
        self.quarantine = Document(self.db, 'quarantine')

    async def setup(self):
        self.config = await self.dbconfig.find({'_id': self.bot.user.id})
        if not self.config:
            return None
        else:
            return self.config

    async def punish(self, user: discord.Member | discord.User, guild: discord.Guild, Moderator: discord.Member | str, punishment: PunishmentType, target: discord.TextChannel | discord.VoiceChannel | discord.CategoryChannel | discord.ForumChannel | discord.Role | discord.Webhook):

        try:
            await user.send(f"You have Triggered a Security Rule in {target.guild.name} and the following action has been taken: `{punishment.name.capitalize()}`")
        except discord.Forbidden:
                pass
        
        match punishment:
            case PunishmentType.KICK:
                await user.kick(reason="Security Rule Triggered")            

            case PunishmentType.BAN:
                await user.ban(reason="Security Rule Triggered")

            case PunishmentType.TIMEOUT:
                await user.edit(timed_out_until=datetime.datetime.utcnow() + datetime.timedelta(days=25))
                
            case PunishmentType.Quarantine:
                user_roles: List[discord.Role] = []                
                for role in user.roles:
                    if role >= guild.me.top_role: continue
                    if role.managed: continue
                    if role.id == self.config['quarantineRole']: continue
                    user_roles.append(role)
                
                quarantine_data: Quarantine = {
                    '_id': user.id,
                    'user_id': user.id,
                    'guild_id': guild.id,
                    'quarantine_by': Moderator.id if isinstance(Moderator, discord.Member) else Moderator,
                    'reason': "Security Rule Triggered",
                    'roles': [role.id for role in user_roles]
                }

                await user.remove_roles(*user_roles, reason="Quaranting User")
                await user.add_roles(guild.get_role(self.config['quarantineRole']), reason="Quaranting User")
                await self.quarantine.insert(quarantine_data)

            
        await self.send_log(user=user, guild=guild, Moderator=Moderator, action=punishment, reason="Security Rule Triggered", target=target)


    async def send_log(self, user: discord.Member | discord.User, guild: discord.Guild, Moderator: discord.Member | str, action: PunishmentType, reason: str, target: discord.TextChannel | discord.VoiceChannel | discord.CategoryChannel | discord.ForumChannel | discord.Role | discord.Webhook):
        log_channel = guild.get_channel(self.config['log_channel'])
        if not log_channel: return

        embed = discord.Embed(description=f"<:tgk_description:1215649279360897125> `Security Report`\n\n", color=self.bot.default_color)
        embed_args = await get_formated_embed(["User", "Moderator", "Action", "Target", "Reason"])

        embed.description += f"{get_formated_field(guild, embed_args['User'], 'user', user.id)}\n"
        embed.description += f"{get_formated_field(guild, embed_args['Moderator'], 'user', Moderator.id if isinstance(Moderator, discord.Member) else Moderator)}\n"
        embed.description += f"{get_formated_field(guild, embed_args['Action'], 'str', action)}\n"
        embed.description += f"{get_formated_field(guild, embed_args['Target'], 'role', target.id)}\n" if isinstance(target, discord.Role) else f"{get_formated_field(guild, 'Target', 'channel', target.id)}\n"
        embed.description += f"{get_formated_field(guild, embed_args['Reason'], 'str', reason)}\n"

        await log_channel.send(embed=embed)