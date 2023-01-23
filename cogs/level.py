import discord
import datetime
import pandas as pd
from discord import app_commands, Interaction
from discord.ext import commands, tasks
from utils.db import Document
from utils.transformer import MutipleRole, MutipleChannel, MultipleMember
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO


class level(commands.GroupCog, name="level"):
    def __init__(self, bot):
        self.bot = bot
        self.bot.level_config = Document(self.bot.db, "leveling")
        self.bot.level_config_cache = {}
    
    def template_db(self, guild_id:int) -> dict:
        return {
            "_id": guild_id,
            "blacklist": {
                "channels": [],
                "roles": [],
            },
            'multiplier': {
                'channels': {},
                'roles': {},
            },
            'cooldown': 8,
            'cleanup_on_leave': True,
        }

    blacklist = app_commands.Group(name="blacklist", description="Blacklist a channel or role from leveling")
    multiplier = app_commands.Group(name="multiplier", description="Configure the multiplier for leveling")
    config = app_commands.Group(name="config", description="Configure the leveling system")
    manage = app_commands.Group(name="manage", description="Manage exp for a user")

    @blacklist.command(name="channel", description="Add/Remove a channel from the blacklist")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(channel="The channel to blacklist")
    async def blacklist_channel(self, interaction: Interaction, channel: discord.TextChannel):
        data = await self.bot.level_config.find(interaction.guild.id)
        if not data:
            data = self.template_db(interaction.guild.id)
            await self.bot.level_config.insert(data)

        if channel.id in data['blacklist']['channels']:
            data['blacklist']['channels'].remove(channel.id)
            await interaction.response.send_message(embed=discord.Embed(description=f"<:dynosuccess:1000349098240647188> | Channel {channel.mention} Suscessfully removed from blacklist", color=0x363940))

        else:
            data['blacklist']['channels'].append(channel.id)
            await interaction.response.send_message(embed=discord.Embed(description=f"<:dynosuccess:1000349098240647188> | Channel {channel.mention} Suscessfully blacklisted", color=0x363940))

        await self.bot.level_config.update(data)
        self.bot.level_config_cache[interaction.guild.id] = data


    @blacklist.command(name="role", description="Add/Remove a role from the blacklist")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(role="The role to blacklist")
    async def blacklist_role(self, interaction: Interaction, role: discord.Role):
        data = await self.bot.level_config.find(interaction.guild.id)
        if not data:
            data = self.template_db(interaction.guild.id)
            await self.bot.level_config.insert(data)

        if role.id in data['blacklist']['roles']:
            data['blacklist']['roles'].remove(role.id)
            await interaction.response.send_message(embed=discord.Embed(description=f"<:dynosuccess:1000349098240647188> | Role {role.mention} Suscessfully removed from blacklist",color=0x363940))

        else:
            data['blacklist']['roles'].append(role.id)
            await interaction.response.send_message(embed=discord.Embed(description=f"<:dynosuccess:1000349098240647188> | Role {role.mention} Suscessfully blacklisted",color=0x363940))

        await self.bot.level_config.update(data)
        self.bot.level_config_cache[interaction.guild.id] = data

    @multiplier.command(name="set", description="Set the multiplier for a channel or role")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(multiplier="The multiplier to set", channels="The channel to set the multiplier for", roles="The role to set the multiplier for")
    async def multiplier_set(self, interaction: Interaction, multiplier: app_commands.Range[int, 1, 10], channels: app_commands.Transform[discord.TextChannel, MutipleChannel] = None, roles: app_commands.Transform[discord.Role, MutipleRole] = None):
        data = await self.bot.level_config.find(interaction.guild.id)
        if not data:
            data = self.template_db(interaction.guild.id)
            await self.bot.level_config.insert(data)

        await interaction.response.send_message(embed=discord.Embed(description=f"<a:loading:998834454292344842> | Please wait while we update the multipliers", color=0x363940))

        description = ""

        for channel in channels:
            data['multiplier']['channels'][str(channel.id)] = multiplier
            description += f"<:dynosuccess:1000349098240647188> | {channel.mention} <:join:991733999477203054> {multiplier}x\n"
        
        for role in roles:
            data['multiplier']['roles'][str(role.id)] = multiplier
            description += f"<:dynosuccess:1000349098240647188> | {role.mention} <:join:991733999477203054> {multiplier}x\n"
        
        await self.bot.level_config.update(data)
        self.bot.level_config_cache[interaction.guild.id] = data
        await interaction.edit_original_response(embed=discord.Embed(description=description,color=0x363940))


    @multiplier.command(name="remove", description="Remove the multiplier for a channel or role")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(channels="The channel to remove the multiplier for", roles="The role to remove the multiplier for")
    async def multiplier_remove(self, interaction: Interaction, channels: MutipleChannel = None, roles: MutipleRole = None):
        data = await self.bot.level_config.find(interaction.guild.id)
        if not data:
            data = self.template_db(interaction.guild.id)
            await self.bot.level_config.insert(data)

        await interaction.response.send_message(embed=discord.Embed(description=f"<a:loading:998834454292344842> | Please wait while we update the multipliers", color=0x363940))

        description = ""

        for channel in channels:
            data['multiplier']['channels'].pop(str(channel.id), None)
            description += f"<:dynosuccess:1000349098240647188> | {channel.mention} <:join:991733999477203054> Removed\n"
        
        for role in roles:
            data['multiplier']['roles'].pop(str(role.id), None)
            description += f"<:dynosuccess:1000349098240647188> | {role.mention} <:join:991733999477203054> Removed\n"
        
        await self.bot.level_config.update(data)
        self.bot.level_config_cache[interaction.guild.id] = data
        await interaction.edit_original_response(embed=discord.Embed(description=description,color=0x363940))
    
    @config.command(name="show", description="Show the current level config")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def show(self, interaction: Interaction):
        await interaction.response.send_message(embed=discord.Embed(description=f"<a:loading:998834454292344842> | Please wait while we fetch the config", color=0x363940))
        data = await self.bot.level_config.find(interaction.guild.id)
        if not data:
            data = self.template_db(interaction.guild.id)
            await self.bot.level_config.insert(data)

        role_multiplier = {role: multiplier for role, multiplier in data['multiplier']['roles'].items() if multiplier != 1}
        channel_multiplier = {channel: multiplier for channel, multiplier in data['multiplier']['channels'].items() if multiplier != 1}

        embed = discord.Embed(title="Level Config", color=0x363940)
        embed.add_field(name="Global Multiplier", value="`1`")
        embed.add_field(name="Role Multipliers", value="\n".join([f"<@&{role}>: `{multiplier}x`" for role, multiplier in role_multiplier.items()]) or "`None`")
        embed.add_field(name="Channel Multipliers", value="\n".join([f"<#{channel}>: `{multiplier}x`" for channel, multiplier in channel_multiplier.items()]) or "`None`")        
        embed.add_field(name="Blacklisted Channels", value="\n".join([f"<#{channel}>" for channel in data['blacklist']['channels']]) or "`None`")
        embed.add_field(name="Blacklisted Roles", value="\n".join([f"<@&{role}>" for role in data['blacklist']['roles']]) or "`None`")
        embed.add_field(name="Clear on Leave", value="<:octane_yes:1019957051721535618> on" if data['clear_on_leave'] else "<:octane_no:1019957208466862120> off")
        embed.add_field(name="Cooldown", value=f"`{data['cooldown']}s`")

        await interaction.edit_original_response(embed=embed)
        
    @config.command(name="clear-on-leave", description="Clear the user's level on leave")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(state="The state to set the clear on leave to")
    async def clear_on_leave(self, interaction: Interaction, state: bool):
        data = await self.bot.level_config.find(interaction.guild.id)
        if not data:
            data = self.template_db(interaction.guild.id)
            await self.bot.level_config.insert(data)

        data['clear_on_leave'] = state
        await self.bot.level_config.update(data)
        self.bot.level_config_cache[interaction.guild.id] = data
        await interaction.response.send_message(embed=discord.Embed(description=f"<:dynosuccess:1000349098240647188> | Cleared on leave set to {state}", color=0x363940))        
    
    @manage.command(name="add", description="give a user a exp")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(users="The users to add exp to", amount="The amount of exp to add")
    async def add(self, interaction: Interaction, users: app_commands.Transform[discord.Member, MultipleMember], amount: int):
        await interaction.response.send_message(embed=discord.Embed(description=f"<a:loading:998834454292344842> | Please wait while we add the exp", color=0x363940))
        description = ""
        for user in users:
            data = await self.bot.ranks.find(user.id)
            if not data:
                Level_BackEnd.template_db(user.id)
                await self.bot.ranks.insert(data)
            data['xp'] += amount
            await self.bot.ranks.update(data)
            self.bot.rank_cache[user.id] = data
            description += f"<:dynosuccess:1000349098240647188> | {user.mention} <:join:991733999477203054> + `{amount}` exp\n"
        
        await interaction.edit_original_response(embed=discord.Embed(description=description,color=0x363940))
    
    @manage.command(name="remove", description="remove a user's exp")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(users="The users to remove exp from", amount="The amount of exp to remove")
    async def remove(self, interaction: Interaction, users: app_commands.Transform[discord.Member, MultipleMember], amount: int):
        await interaction.response.send_message(embed=discord.Embed(description=f"<a:loading:998834454292344842> | Please wait while we remove the exp", color=0x363940))
        description = ""
        for user in users:
            data = await self.bot.ranks.find(user.id)
            if not data:
                Level_BackEnd.template_db(user.id)
                await self.bot.ranks.insert(data)
            data['xp'] -= amount
            await self.bot.ranks.update(data)
            self.bot.rank_cache[user.id] = data
            description += f"<:dynosuccess:1000349098240647188> | {user.mention} <:join:991733999477203054> - `{amount}` exp\n"
        
        await interaction.edit_original_response(embed=discord.Embed(description=description,color=0x363940))
    
    @manage.command(name="set", description="set a user's exp")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(users="The users to set exp to", amount="The amount of exp to set")
    async def set(self, interaction: Interaction, users: app_commands.Transform[discord.Member, MultipleMember], amount: int):
        await interaction.response.send_message(embed=discord.Embed(description=f"<a:loading:998834454292344842> | Please wait while we set the exp", color=0x363940))
        description = ""
        for user in users:
            data = await self.bot.ranks.find(user.id)
            if not data:
                Level_BackEnd.template_db(user.id)
                await self.bot.ranks.insert(data)
            data['xp'] = amount
            await self.bot.ranks.update(data)
            self.bot.rank_cache[user.id] = data
            
        
        await interaction.edit_original_response(embed=discord.Embed(description=description,color=0x363940))


class Level_BackEnd(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.ranks = Document(self.bot.db, "ranks")
        self.bot.rank_cache = {}
        self.bot.rank_in_progress = {}
        self.bot.level_config_task = self.update_level_config.start()

    def cog_unload(self):
        self.bot.level_config_task.cancel()

    @staticmethod
    def template_db(user_id):
        return {
            "_id": user_id,
            "xp": 0,
            "last_updated": None,
        }
    
    
    async def create_level_card(self, user: discord.Member, rank: int, exp: int):
        base_image = Image.open('./assets/level_template.png')
        profile = user.avatar.with_format('png')
        profile = BytesIO(await profile.read())
        profile = Image.open(profile)
        profile = profile.resize((217, 217), Image.Resampling.LANCZOS).convert('RGBA')

        draw = ImageDraw.Draw(base_image)
        name_font = ImageFont.truetype('arial.ttf', 38)
        other_font = ImageFont.truetype('arial.ttf', 32)
        base_image.paste(profile, (33, 32))

        draw.text((290, 46), f"{user.name}", (255, 255, 255), font=name_font)
        draw.text((528, 122), f"{rank}", (255, 255, 255), font=other_font)
        draw.text((528, 182), f"{exp}", (255, 255, 255), font=other_font)

        return base_image


    async def get_rank(self, user_id):
        if user_id in self.bot.rank_cache.keys():
            return self.bot.rank_cache[user_id]
        else:
            data = await self.bot.ranks.find(user_id)
            if not data: 
                data = self.template_db(user_id)
                self.bot.rank_cache[user_id] = data
                await self.bot.ranks.insert(data)
            return data

    async def update_rank(self, user_id, data):
        await self.bot.ranks.update(data)
        self.bot.rank_cache[user_id] = data
        print(self.bot.rank_cache)
    
    @tasks.loop(seconds=60)
    async def update_level_config(self):
        config = await self.bot.level_config.get_all()
        for guild in config: self.bot.level_config_cache[guild['_id']] = guild

    @update_level_config.before_loop
    async def before_update_level_config(self):
        await self.bot.wait_until_ready()
    
    @commands.Cog.listener()
    async def on_ready(self):
        config = await self.bot.level_config.get_all()
        for guild in config: self.bot.level_config_cache[guild['_id']] = guild
        print(self.bot.level_config_cache)
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild: return
        if message.author.id == self.bot.user.id: return

        if message.channel.id in self.bot.level_config_cache[message.guild.id]['blacklist']['channels']: return

        if message.author.bot and message.interaction != None: 
            self.bot.dispatch("slash_command", message)
        elif not message.author.bot:
            self.bot.dispatch("update_xp", message)
        

    @commands.Cog.listener()
    async def on_update_xp(self, message):
        if message.author.id in self.bot.rank_in_progress.keys(): return
        user_data = await self.get_rank(message.author.id)
        exp = 1
        multiplier = 1

        if user_data['last_updated'] != None:
            if (datetime.datetime.utcnow() - user_data['last_updated']).total_seconds() < 8:
                try:
                    self.bot.rank_in_progress.pop(message.author.id)
                except KeyError:
                    pass
                return        
    
        role_multiplier = {role: multiplier for role, multiplier in self.bot.level_config_cache[message.guild.id]['multiplier']['roles'].items() if multiplier != 1}
        channel_multiplier = {channel: multiplier for channel, multiplier in self.bot.level_config_cache[message.guild.id]['multiplier']['channels'].items() if multiplier != 1}
        
        for role in message.author.roles:
            if str(role.id) in role_multiplier.keys():
                multiplier += role_multiplier[str(role.id)]
        
        if str(message.channel.id) in channel_multiplier.keys():
            multiplier += channel_multiplier[str(message.channel.id)]
        
        print(f"Role Multiplier: {role_multiplier}\nChannel Multiplier: {channel_multiplier}\nMultiplier: {multiplier}")

        user_data['xp'] += exp * multiplier
        user_data['last_updated'] = datetime.datetime.utcnow()
        await self.update_rank(message.author.id, user_data)
        print(f"{message.author} has gained {exp * multiplier} xp")

        try:
            self.bot.rank_in_progress.pop(message.author.id)
        except KeyError:
            pass

    @commands.Cog.listener()
    async def on_slash_command(self, message):
        if message.author.id in self.bot.rank_in_progress.keys(): return
        user = message.interaction.user
        user_data = await self.get_rank(user.id)
        exp, multiplier = 1, 1

        if (datetime.datetime.utcnow() - user_data['last_updated']).total_seconds() < 8:
            try:
                self.bot.rank_in_progress.pop(user.id)
            except KeyError:
                pass

            print('Cooldown')
            return
        
        else:

            role_multiplier = {role: multiplier for role, multiplier in self.bot.level_config_cache[message.guild.id]['multiplier']['roles'].items() if multiplier != 1}
            channel_multiplier = {channel: multiplier for channel, multiplier in self.bot.level_config_cache[message.guild.id]['multiplier']['channels'].items() if multiplier != 1}
            
            for role in user.roles:
                if str(role.id) in role_multiplier.keys():
                    multiplier += role_multiplier[str(role.id)]
            
            if str(message.channel.id) in channel_multiplier.keys():
                multiplier += channel_multiplier[str(message.channel.id)]
            
            user_data['xp'] += exp * multiplier
            user_data['last_updated'] = datetime.datetime.utcnow()
            await self.update_rank(user.id, user_data)
            print(f"{user} has gained {exp * multiplier} xp")

            try:
                self.bot.rank_in_progress.pop(user.id)
            except KeyError:
                pass

    @app_commands.command(name="rank", description="Get your or another users rank")
    @app_commands.describe(user="The user to get the rank of")
    async def rank(self, interaction: Interaction, user: discord.Member = None):
        user = user if user else interaction.user
        
        await interaction.response.send_message(embed=discord.Embed(description=f"<a:loading:998834454292344842> | Loading {user}'s rank...", color=0x363940))

        ranks = await self.bot.ranks.get_all()
        df = pd.DataFrame(ranks)
        df = df.sort_values(by="xp",ascending = False)
        df = df.reset_index(drop=True)
        rank = df.index[df['_id'] == user.id].tolist()[0] + 1
        data = df.loc[rank - 1].to_dict()

        print(data, rank, str(data['xp']))

        image = await self.create_level_card(user, data['xp'], rank)

        with BytesIO() as image_binary:
            image.save(image_binary, 'PNG')
            image_binary.seek(0)
            await interaction.edit_original_response(embed=None, attachments=[discord.File(fp=image_binary, filename=f'{user.id}_rank_card.png')])

async def setup(bot):
    await bot.add_cog(level(bot))
    await bot.add_cog(Level_BackEnd(bot))


