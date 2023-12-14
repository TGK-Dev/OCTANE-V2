from discord.ext import commands, tasks
from discord import app_commands
from utils.paginator import Paginator
from typing import List
from utils.transformer import TimeConverter
from humanfriendly import format_timespan
from .db import *
from utils.views.selects import Select_General
import datetime
import discord


class Blacklist_cog(commands.GroupCog, name="blacklist"):
    def __init__(self, bot):
        self.bot = bot
        self.backend = backend(bot)
        self.bot.blacklist = self.backend
        self.unblacklist_task = self.unblacklist.start()
        self.check_strike.start()
        self.unbl_task = False
        self.str_task = False

    user = app_commands.Group(name="user", description="Blacklist user")

    strike = app_commands.Group(name="strike", description="Manage strikes of user")

    def cog_unload(self):
        self.unblacklist_task.cancel()
        self.check_strike.cancel()

    async def profile_aucto_normal(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        config = await self.backend.get_config(interaction.guild_id)
        profiles: List[str] = [profile['_id'] for profile in config['profiles'].values() if profile['type'] == "normal"]
        choices = [
            app_commands.Choice(name=profile, value=profile)
            for profile in profiles if current.lower() in profile.lower()
        ]
        return choices[:24]

    async def profile_auto_strike(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        config = await self.backend.get_config(interaction.guild_id)
        profiles: List[str] = [profile['_id'] for profile in config["profiles"].values() if profile['type'] == "strike"]
        choices = [
            app_commands.Choice(name=profile, value=profile)
            for profile in profiles if current.lower() in profile.lower()
        ]
        return choices[:24]
    

    @tasks.loop(minutes=1)
    async def unblacklist(self):
        if self.unbl_task: return
        self.unbl_task = True
        now = datetime.datetime.utcnow()
        data = await self.backend.blacklist.get_all()
        for blacklist in data:
            if blacklist["Blacklist_end"] < now:
                guild = self.bot.get_guild(blacklist["guild_id"])
                user = guild.get_member(blacklist["user_id"])
                if not user:
                    blacklist["Blacklist_end"] = now + datetime.timedelta(seconds=blacklist["Blacklist_duration"])
                    await self.backend.blacklist.update(blacklist)
                    continue
                self.bot.dispatch("blacklist_remove", blacklist)
            else:
                continue
        self.unbl_task = False
    
    @tasks.loop(minutes=10)
    async def check_strike(self):
        if self.str_task: return
        self.str_task = True
        now = datetime.datetime.utcnow()
        guilds = await self.backend.config.get_all()

        for guild in guilds:
            config: Config = guild
            guild = self.bot.get_guild(config['_id'])
            if not guild: 
                await self.backend.config.delete({"guild_id": guild['guild_id']})
                continue
            
            strikes = await self.backend.strike.find_many_by_custom({"guild_id": guild.id})

            for user in strikes:
                member = guild.get_member(user['user_id'])
                profile: Profile = config['profiles'][user['profile']]

                if not member:
                    for strike in user['strikes']:
                        strike['Strike_expire'] = now + datetime.timedelta(seconds=profile['strike_expire'])
                    await self.backend.strike.update(user)
                    continue

                current_strikes = len(user['strikes'])
                for strike in user['strikes']:
                    if now >= strike['Strike_expire']:
                        user['strikes'].remove(strike)
                
                if len(user['strikes']) == 0:
                    await self.backend.strike.delete(user['_id'])
                    continue

                if len(user['strikes']) != current_strikes:
                    await self.backend.strike.update(user)            

        self.str_task = False
    
    @check_strike.before_loop
    async def before_check_strike(self):
        await self.bot.wait_until_ready()
    
    @check_strike.error
    async def check_strike_error(self, error):
        self.str_task = False
    
    @unblacklist.error
    async def unblacklist_error(self, error):
        self.unbl_task = False

    @unblacklist.before_loop
    async def before_unblacklist(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_blacklist_remove(self, blacklist:dict):
        guild = self.bot.get_guild(blacklist["guild_id"])
        user = guild.get_member(blacklist["user_id"])
        config = await self.backend.get_config(guild.id)
        profile: Profile = config['profiles'][blacklist['profile']]
        role_remove = [guild.get_role(role) for role in profile.role_add]
        role_add = [guild.get_role(role) for role in profile.role_remove]
        await user.remove_roles(*role_remove, reason="Blacklist expired")
        await user.add_roles(*role_add, reason="Blacklist expired")

        if config['log_channel']:
            channel = guild.get_channel(config['log_channel'])
            embed = discord.Embed(title="Blacklist expired", color=self.bot.default_color, description="")
            embed.description += f"**User:** {user.mention} ({user.id})\n"
            embed.description += f"**Profile:** {profile._id}\n"
            embed.description += f"**Reason:** {blacklist['Blacklist_reason']}\n"
            embed.description += f"**By:** <@{blacklist['Blacklist_by']}> ({blacklist['Blacklist_by']})\n"

            await channel.send(embed=embed)
        await self.backend.blacklist.delete({"user_id": user.id, "profile": profile._id, "guild_id": guild.id})

    @commands.Cog.listener()
    async def on_ready(self):
        await self.backend.setup()

    async def interaction_check(self, interaction: discord.Interaction):
        config = await self.backend.get_config(interaction.guild_id)
        if config is None:
            return False
        
        if interaction.command.name == "viewmystrike":
            return True

        author_role = [role.id for role in interaction.user.roles]
        if not (set(author_role) & set(config['mod_roles'])):
            await interaction.response.send_message("You don't have permission to use this command", ephemeral=True)
            return False
        return True
        

    @user.command(name="add", description="apply blacklist to user")
    @app_commands.describe(profile="Profile to apply blacklist", user="User to blacklist", reason="Reason for blacklist", duration="Duration of blacklist")
    @app_commands.autocomplete(profile=profile_aucto_normal)
    async def user_add(self, interaction: discord.Interaction, profile: str, user: discord.Member, reason: str, duration: app_commands.Transform[int, TimeConverter]):
        config = await self.backend.get_config(interaction.guild_id)
        if profile not in config["profiles"].keys():
            return await interaction.response.send_message(f"Profile `{profile}` not found", ephemeral=True)
        profile_data: Profile = config["profiles"][profile]

        user_data = await self.backend.get_blacklist(user, profile_data)
        if user_data is not None:
            return await interaction.response.send_message(f"{user.mention} is already blacklisted in profile `{profile}`", ephemeral=True)
        user_data: Blacklist = {
            "user_id": user.id,
            "guild_id": interaction.guild_id,
            "profile": profile_data["_id"],
            "Blacklist_at": datetime.datetime.utcnow(),
            "Blacklist_by": interaction.user.id,
            "Blacklist_reason": reason,
            "Blacklist_duration": duration,
            "Blacklist_end": datetime.datetime.utcnow() + datetime.timedelta(seconds=duration)            
        }
        await self.backend.insert_blacklist(user_data)

        role_add = [interaction.guild.get_role(role_id) for role_id in profile_data['add_role']]
        role_remove = [interaction.guild.get_role(role_id) for role_id in profile_data['role_remove']]
        await user.add_roles(*role_add, reason=f"Blacklist by {interaction.user} ({interaction.user.id})")
        await user.remove_roles(*role_remove, reason=f"Blacklist by {interaction.user} ({interaction.user.id})")

        await interaction.response.send_message(f"{user.mention} has been blacklisted in profile `{profile}`", ephemeral=True)

        if config:
            channel: discord.TextChannel = interaction.guild.get_channel(config['log_channel'])
            embed = discord.Embed(title="Blacklist", description=f"", color=discord.Color.red())
            embed.description += f"**User:** {user.mention} ({user.id})\n"
            embed.description += f"**Profile:** {profile}\n"
            embed.description += f"**Reason:** {reason}\n"
            embed.description += f"**Duration:** {format_timespan(duration)}\n"
            embed.description += f"**End:** <t:{int((datetime.datetime.now() + datetime.timedelta(seconds=duration)).timestamp())}:R>\n"
            embed.description += f"**By:** {interaction.user.mention} ({interaction.user.id})\n"
            await channel.send(embed=embed)

    @user.command(name="remove", description="remove blacklist from user")
    @app_commands.describe(profile="Profile to remove blacklist", user="User to remove blacklist", reason="Reason for removing blacklist")
    @app_commands.autocomplete(profile=profile_aucto_normal)
    async def user_remove(self, interaction: discord.Interaction, profile: str, user: discord.Member, reason: str=None):
        config = await self.backend.get_config(interaction.guild_id)
        if profile not in config['profiles'].keys():
            return await interaction.response.send_message(f"Profile `{profile}` not found", ephemeral=True)
        
        profile_data: Profile = config["profiles"][profile]

        user_data = await self.backend.get_blacklist(user, profile_data)
        if user_data is None:
            return await interaction.response.send_message(f"{user.mention} is not blacklisted in profile `{profile}`", ephemeral=True)

        role_add = [interaction.guild.get_role(role_id) for role_id in profile_data['remove_role']]
        role_remove = [interaction.guild.get_role(role_id) for role_id in profile_data['role_add']]
        await user.add_roles(*role_add, reason=f"Blacklist removed by {interaction.user} ({interaction.user.id})")
        await user.remove_roles(*role_remove, reason=f"Blacklist removed by {interaction.user} ({interaction.user.id})")

        await interaction.response.send_message(f"{user.mention} has been removed from blacklist in profile `{profile}`", ephemeral=True)
        await self.backend.blacklist.delete({"user_id": user.id, "profile": profile_data['_id'], "guild_id": interaction.guild_id})

    @user.command(name="view", description="View blacklist of user")
    @app_commands.describe(user="User to view blacklist")
    async def _view(self, interaction: discord.Interaction, user: discord.Member):
        config = await self.backend.get_config(interaction.guild_id)
        if config is None:
            return await interaction.response.send_message("This server doesn't have blacklist", ephemeral=True)
        pages = []
        for blacklist in await self.backend.blacklist.find_many_by_custom({"user_id": user.id, "guild_id": interaction.guild_id}):
            profile:Profile = config['profiles'][blacklist['profile']]
            embed = discord.Embed(title=f"Blacklist of {user}", color=self.bot.default_color, description="")
            embed.description += f"**Profile:** {profile._id}\n"
            embed.description += f"**Reason:** {blacklist['Blacklist_reason']}\n"
            embed.description += f"**Duration:** {format_timespan(blacklist['Blacklist_duration'])}\n"
            embed.description += f"**End:** <t:{int(blacklist['Blacklist_end'].timestamp())}:R>\n"
            embed.description += f"**By:** <@{blacklist['Blacklist_by']}> ({blacklist['Blacklist_by']})\n"
            pages.append(embed)
        if len(pages) == 0:
            return await interaction.response.send_message(f"{user.mention} is not blacklisted", ephemeral=True)
        if len(pages) == 1:
            await interaction.response.send_message(embed=pages[0], ephemeral=False)
        else:
            await Paginator(interaction, pages=pages).start(embeded=True,quick_navigation=False, hidden=False)

    @strike.command(name="add", description="Add strike to user")
    @app_commands.describe(profile="Profile to add strike", user="User to add strike", reason="Reason for adding strike")
    @app_commands.autocomplete(profile=profile_auto_strike)
    async def _strick_add(self, interaction: discord.Interaction, profile: str, user: discord.Member, reason: str):
        config = await self.backend.get_config(interaction.guild_id)
        if config is None:
            return await interaction.response.send_message("This server doesn't have blacklist", ephemeral=True)
        if profile not in config['profiles'].keys():
            return await interaction.response.send_message(f"Profile `{profile}` not found", ephemeral=True)
        profile_data: Profile = config['profiles'][profile]
        
        await interaction.response.send_message("Adding strike...", ephemeral=True)
        strike: StrikeUser = await self.backend.strike.find({"user_id": user.id, "guild_id": interaction.guild_id, "profile": profile_data["_id"]})
        if strike is None:
            strike: StrikeUser =  {
                "user_id": user.id,
                "guild_id": interaction.guild_id,
                "profile": profile_data["_id"],
                "strikes": []
            }
            await self.backend.strike.insert(strike)
        
        strike['strikes'].append({
            "Strike_at": datetime.datetime.utcnow(),
            "Strike_by": interaction.user.id,
            "Strike_reason": reason,
            "Strike_expire": datetime.datetime.utcnow() + datetime.timedelta(seconds=profile_data['strike_expire'])
        })

        await self.backend.strike.upsert(strike)
        
        if len(strike['strikes']) >= profile_data['strike_limit']:
            await interaction.edit_original_response(content=f"{user.mention} has reached strike limit in profile `{profile}` applying blacklist...")
            user_blacklist: Blacklist = {
                "user_id": user.id,
                "guild_id": interaction.guild_id,
                "profile": profile_data["_id"],
                "Blacklist_at": datetime.datetime.utcnow(),
                "Blacklist_by": interaction.user.id,
                "Blacklist_reason": "Reached strike limit",
                "Blacklist_duration": profile_data["strike_expire"],
                "Blacklist_end": datetime.datetime.utcnow() + datetime.timedelta(seconds=profile_data["strike_expire"])
            }
            await self.backend.blacklist.insert(user_blacklist)
            await self.backend.strike.delete(strike)
            role_add = [interaction.guild.get_role(role_id) for role_id in profile_data['role_add']]
            role_remove = [interaction.guild.get_role(role_id) for role_id in profile_data['role_remove']]
            await user.add_roles(*role_add, reason=f"Blacklist by {interaction.user} ({interaction.user.id})")
            await user.remove_roles(*role_remove, reason=f"Blacklist by {interaction.user} ({interaction.user.id})")
            await interaction.edit_original_response(content=f"{user.mention} has been blacklisted in profile `{profile}`")

            try:
                embed = discord.Embed(title=f"You have been blacklisted in profile {profile}", description=f"", color=self.bot.default_color)
                embed.description += f"**Reason:** Reached strike limit\n"
                await user.send(embed=embed)
            except:
                pass

            if config['log_channel']:
                channel = interaction.guild.get_channel(config['log_channel'])
                embed = discord.Embed(title="Blacklist", description=f"", color=discord.Color.red())
                embed.description += f"**User:** {user.mention} ({user.id})\n"
                embed.description += f"**Profile:** {profile}\n"
                embed.description += f"**Reason:** Reached strike limit\n"
                embed.description += f"**Duration:** {format_timespan(profile_data['strike_expire'])}\n"
                embed.description += f"**End:** <t:{int((datetime.datetime.now() + datetime.timedelta(seconds=profile_data['strike_expire'])).timestamp())}:R>\n"
                embed.description += f"**By:** {interaction.user.mention} ({interaction.user.id})\n"
                await channel.send(embed=embed)
        else:
            await interaction.edit_original_response(content=f"{user.mention} has been given strike in profile `{profile}` ({len(strike['strikes'])}/{profile_data['strike_limit']})")
            try:
                embed = discord.Embed(title=f"You have been given a strike in profile {profile}", description=f"", color=self.bot.default_color)
                embed.description += f"**Reason:** {reason}\n"
                embed.description += f"**Strikes:" + "<:tgk_red:1184768688335900702> "*len(strike['strikes']) + "<:tgk_white:1184768731033895012>"*(profile_data['strike_limit']-len(strike['strikes'])) + "**\n"
                embed.set_footer(text="Reaching strike limit will automatically blacklist you")
                await user.send(embed=embed)
            except discord.HTTPException:
                pass
    
    @strike.command(name="remove", description="Remove strike from user")
    @app_commands.describe(profile="Profile to remove strike", user="User to remove strike", reason="Reason for removing strike")
    @app_commands.autocomplete(profile=profile_auto_strike)
    async def _strick_remove(self, interaction: discord.Interaction, user: discord.Member, profile: str):
        config: Config = await self.backend.get_config(interaction.guild_id)
        if config is None:
            return await interaction.response.send_message("This server doesn't have blacklist", ephemeral=True)
        
        user_data = await self.backend.strike.find({"user_id": user.id, "guild_id": interaction.guild_id, "profile": profile})
        if user_data is None:
            return await interaction.response.send_message(f"{user.mention} has no strike in profile `{profile}`", ephemeral=True)
        
        embed = discord.Embed(title=f"Strikes of {user}", color=self.bot.default_color, description="")
        embed.description += f"**Profile:** {profile}\n"
        embed.description += "**Total Strikes:** " + "<:tgk_red:1184768688335900702> "*len(user_data['strikes']) + "<:tgk_white:1184768731033895012>"*(config['profiles'][profile]['strike_limit']-len(user_data['strikes'])) + "\n"
        embed.description += f"**Oldest Strike Expire In: ** <t:{int(user_data['strikes'][0]['Strike_expire'].timestamp())}:R>\n"

        view = discord.ui.View(timeout=120)
        options = []

        for index, strike in enumerate(user_data['strikes']):
            embed.add_field(name=f"Strike {index+1}", value=f"**Reason:** {strike['Strike_reason']}\n**By:** <@{strike['Strike_by']}> ({strike['Strike_by']})\n**At:** <t:{int(strike['Strike_at'].timestamp())}:R>\n**Expire In:** <t:{int(strike['Strike_expire'].timestamp())}:R>", inline=False)
            options.append(discord.SelectOption(
                label=f"Strike {index+1}",
                description=f"{strike['Strike_reason']}",
                value=f"{index+1}",
                emoji="<:tgk_messagePing:1091682102824681553>"
            ))
        view.select = Select_General(options=options, placeholder="Select strike to remove", min_values=1, max_values=len(options))
        view.add_item(view.select)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=False)

        await view.wait()
        view.select.disabled = True
        if view.value is None or view.value is False:
            return await interaction.edit_original_message(view=view)
            
        for index in view.select.values:
            user_data['strikes'].pop(int(index)-1)
        
        await view.select.interaction.response.send_message("Removing strike...", ephemeral=True)
        await self.backend.strike.update(user_data)
        await interaction.edit_original_response(view=view)
        await interaction.followup.send(content=f"Suscessfully removed {len(view.select.values)} strike from {user.mention} in profile `{profile}`")


    @app_commands.command(name="viewmystrike", description="View your strikes")
    async def _viewmystrike(self, interaction: discord.Interaction):
        profiles: [StrikeUser] = await self.backend.strike.find_many_by_custom({"user_id": interaction.user.id, "guild_id": interaction.guild_id})
        if len(profiles) == 0:
            return await interaction.response.send_message("You don't have any active strikes", ephemeral=True)
        pages = []
        config = await self.backend.get_config(interaction.guild_id)
        for profile in profiles:
            profile: StrikeUser = profile
            max_strike = config['profiles'][profile['profile']]['strike_limit']
            embed = discord.Embed(title=f"Strikes in profile {profile['profile']}", color=self.bot.default_color, description="")
            embed.description += f"**Profile:** {profile['profile']}\n"
            embed.description += f"**Strikes:** " + "<:tgk_red:1184768688335900702> "*len(profile['strikes']) + "<:tgk_white:1184768731033895012>"*(max_strike-len(profile['strikes'])) + "\n"
            embed.description += f"**Oldest Strike Expire In: ** <t:{int(profile['strikes'][0]['Strike_expire'].timestamp())}:R>"
            pages.append(embed)

        if len(pages) == 1:
            await interaction.response.send_message(embed=pages[0], ephemeral=False)
        else:
            await Paginator(interaction, pages=pages).start(embeded=True,quick_navigation=False, hidden=False)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        config = await self.backend.get_config(member.guild.id)
        if config is None:
            return
        for blacklist in await self.backend.blacklist.find_many_by_custom({"user_id": member.id, "guild_id": member.guild.id}):
            profile: Profile = config['profiles'][blacklist['profile']]
            role_add = [member.guild.get_role(role_id) for role_id in profile.role_add]
            role_remove = [member.guild.get_role(role_id) for role_id in profile.role_remove]

            await member.add_roles(*role_add, reason=f"Presistent blacklist by {member.guild.me} ({member.guild.me.id})")
            await member.remove_roles(*role_remove, reason=f"Presistent blacklist by {member.guild.me} ({member.guild.me.id})")
            blacklist["Blacklist_end"] = datetime.datetime.utcnow() + datetime.timedelta(seconds=blacklist["Blacklist_duration"])
            blacklist["Blacklist_at"] = datetime.datetime.utcnow()
            await self.backend.blacklist.update(blacklist)

async def setup(bot):
    await bot.add_cog(Blacklist_cog(bot))