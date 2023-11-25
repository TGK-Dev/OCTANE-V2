
import datetime
import discord
import asyncio
import re

from discord.ext import commands, tasks
from copy import deepcopy
from discord import app_commands
from utils.db import Document
from typing import List
from utils.views.buttons import Confirm
from utils.checks import is_dev

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.vote_remider_task = self.check_vote_reminders.start()
        self.counter_task = self.update_member_counter.start()
        self.bot.votes = Document(self.bot.db, "votes")
        self.bot.free = Document(self.bot.db, "free")
        self.free_task = self.update_free.start()
        self.activiy_webhook = None
        self.vote_task_progress = False
    
    def cog_unload(self):
        self.vote_remider_task.cancel()
        self.counter_task.cancel()
    
    @commands.Cog.listener()
    async def on_ready(self):
        channel = self.bot.get_channel(1031514773310930945)
        for webhook in await channel.webhooks():
            if webhook.user.id == self.bot.user.id:
                self.activiy_webhook = webhook
        if  not isinstance(self.activiy_webhook, discord.Webhook):
            avatar = await self.bot.user.avatar.read()
            self.activiy_webhook = await channel.create_webhook(name=self.bot.user.name, avatar=avatar)

    @tasks.loop(minutes=5)
    async def update_member_counter(self):
        guild = self.bot.get_guild(785839283847954433)
        member_count = guild.member_count
        channel = guild.get_channel(821747332327931995)
        number = re.findall(r'\d+', channel.name)
        number = int(number[0])
        if number != member_count:
            new_name = f"{channel.name.replace(str(number), str(member_count))}"
            await channel.edit(name=new_name)
    
    @tasks.loop(minutes=5)
    async def update_free(self):
        data = await self.bot.free.get_all()
        now = datetime.datetime.utcnow()
        guild = self.bot.get_guild(785839283847954433)
        for user in data:
            if user['banned'] == False or user['unbanAt'] is None: 
                continue
            if user['unbanAt'] < now:
                member = await self.bot.fetch_user(user['_id'])
                if not isinstance(member, discord.User): continue
                try:
                    await guild.unban(member, reason="Freeloader ban expired")
                except discord.HTTPException:
                    pass
                user['unbanAt'] = None
                user['banned'] = False
                await self.bot.free.update(user)

    @tasks.loop(minutes=1)
    async def check_vote_reminders(self):
        if self.vote_task_progress:
            return
        self.vote_task_progress = True

        current_time = datetime.datetime.utcnow()
        current_data = await self.bot.votes.get_all()
        for data in current_data:
            if data["reminded"] == True: continue
        
            expired_time = data['lastVote'] + datetime.timedelta(hours=12)
            if current_time >= expired_time and data["reminded"] == False:
                self.bot.dispatch("vote_reminder", data)
            
            if expired_time > current_time + datetime.timedelta(days=30):
                await self.bot.votes.delete(data['_id'])
        
        self.vote_task_progress = False
    
    @update_free.before_loop
    async def before_update_free(self):
        await self.bot.wait_until_ready()

    @update_member_counter.before_loop
    async def before_update_member_counter(self):
        await self.bot.wait_until_ready()
    
    @check_vote_reminders.before_loop
    async def before_check_vote_reminders(self):
        await self.bot.wait_until_ready()
    
    @commands.Cog.listener()
    async def on_vote_reminder(self, data):
        if data["reminded"] == True: return

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Vote for TGK at Top.gg", emoji="<a:tgk_icon:1002504426172448828>",url="https://top.gg/servers/785839283847954433/vote"))

        guild = self.bot.get_guild(785839283847954433)
        member = guild.get_member(int(data['discordId']))
        if member is None:
            return await self.bot.votes.delete(data['_id'])

        await member.remove_roles(guild.get_role(786884615192313866))
        data['reminded'] = True
        await self.bot.votes.upsert(data)
        try:
            await member.send("You can now vote for The Gambler's Kingdom again!", view=view)
        except discord.HTTPException:
            pass
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild or message.guild.id != 785839283847954433: return

        if message.channel.id == 1079670945171640360:
            self.bot.dispatch("dank_price_update", message)

        if message.author.id != 270904126974590976: return
        if len(message.embeds) == 0: 
            return
        embed = message.embeds[0]
        if isinstance(embed, discord.Embed) == False: return
        if embed.description is None: return
        if embed.description.startswith("Successfully paid") and embed.description.endswith("from the server's pool!"):
            command_message = await message.channel.fetch_message(message.reference.message_id)
            if command_message.interaction is None: return
            if command_message.interaction.name != "serverevents payout": return

            embed = command_message.embeds[0].to_dict()
            winner = re.findall(r"<@!?\d+>", embed['description'])
            prize = re.findall(r"\*\*(.*?)\*\*", embed['description'])[0]
            emojis = list(set(re.findall(":\w*:\d*", prize)))
            for emoji in emojis :prize = prize.replace(emoji,"",100); prize = prize.replace("<>","",100);prize = prize.replace("<a>","",100);prize = prize.replace("  "," ",100)

            log_embed = discord.Embed(title="Server Events Payout", description=f"",color=self.bot.default_color)
            log_embed.description += f"**Winner**: {winner[0]}\n"
            log_embed.description += f"**Prize**: {prize}\n"
            log_embed.description += f"**Paid by**: {command_message.interaction.user.mention}\n"
            link_view = discord.ui.View()
            link_view.add_item(discord.ui.Button(label="Go to Payout Message", url=command_message.jump_url))
            log_channel = self.bot.get_channel(1076586539368333342)
            await log_channel.send(embed=log_embed, view=link_view)
        elif embed.description.startswith('Successfully donated!') and message.channel.id in [851663580620521472, 812711254790897714, 1051387593318740009, 1116295238584111155, 1086323496788963328]:
            command_message = await message.channel.fetch_message(message.reference.message_id)
            if command_message.interaction is None: return
            if command_message.interaction.name != "serverevents donate": return

            embed = command_message.embeds[0].to_dict()
            donor = command_message.interaction.user
            prize = re.findall(r"\*\*(.*?)\*\*", embed['description'])[0]
            emojis = list(set(re.findall(":\w*:\d*", prize)))
            for emoji in emojis :prize = prize.replace(emoji,"",100); prize = prize.replace("<>","",100);prize = prize.replace("<a>","",100);prize = prize.replace("  "," ",100)

            await command_message.reply(f'{donor.mention} successfully donated **{prize}** to the server pool!', allowed_mentions=discord.AllowedMentions.none())
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return

        elif isinstance(error, commands.CommandOnCooldown):
            return await ctx.send(f"This command is on cooldown for {error.retry_after:.2f} seconds")

        elif isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send(f"Missing required argument {error.param.name}")

        elif isinstance(error, commands.BadArgument):
            return await ctx.send(f"Bad argument {error.param.name}")

        elif isinstance(error, commands.MissingPermissions):
            return await ctx.send(f"You don't have permission to use this command")

        elif isinstance(error, commands.BotMissingPermissions):
            return await ctx.send(f"I don't have permission to use this command")

        elif isinstance(error, commands.CheckFailure):
            return await ctx.send(f"You don't have permission to use this command")

        elif isinstance(error, commands.CommandInvokeError):
            return await ctx.send(f"An error occured while executing this command\n```\n{error}\n```")

        else:
            embed = discord.Embed(color=0xE74C3C,description=f"<:dnd:840490624670892063> | Error: `{error}`")
            await ctx.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_presence_update(self, before, after):
        if before.guild.id != 785839283847954433: return
        supporter_role = before.guild.get_role(992108093271965856)
        if len(after.activities) <= 0 and supporter_role in after.roles:
            await after.remove_roles(supporter_role, reason="No longer supporting")
            return        
        await asyncio.sleep(5)

        for activity in after.activities:
            try:
                if activity.type == discord.ActivityType.custom:
                    if ".gg/tgk" in activity.name.lower():

                        if supporter_role in after.roles: return
                        embed = discord.Embed(description=f"Thanks for supporting the The Gambler's Kingdom\n\nYou have been given the {supporter_role.mention} role", color=supporter_role.color)
                        embed.set_author(name=f"{after.global_name}({after.id})", icon_url=after.avatar.url if after.avatar else after.default_avatar)
                        embed.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar.url)
                        embed.timestamp = datetime.datetime.now()
                        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/869579480509841428.gif?v=1")
                        await self.activiy_webhook.send(embed=embed)
                        await after.add_roles(supporter_role)
                        return

                    elif not ".gg/tgk" in activity.name.lower():                        
                        if supporter_role in after.roles: await after.remove_roles(supporter_role)                        
                        return
            except Exception as e:
                pass
    

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User | discord.Member):
        if guild.id != 785839283847954433: return
        ban = await guild.fetch_ban(user)
        if 'no appeal' in ban.reason.lower():
            appeal_server = self.bot.get_guild(988761284956799038)
            if appeal_server is None: return
            await appeal_server.ban(user, reason="Banned in main server with no appeal tag")
            return

async def setup(bot):
    await bot.add_cog(Events(bot))
    