import discord
import datetime
import asyncio
import humanfriendly
from discord import app_commands
from discord.ext import commands, tasks
from utils.db import Document
from utils.views.payout_system import Payout_Config_Edit
from utils.transformer import MultipleMember
from utils.views.payout_system import Payout_Buttton, Payout_claim
from utils.transformer import TimeConverter
from typing import Literal
from io import BytesIO

auto_payout = {
	1049233574622146560: {'prize': '2 Mil', 'event': '40 Player Rumble'},
	1049233633371750400: {'prize': '3 Mil', 'event': '69 Player Rumble'},
	1049233702355468299: {'prize': '5 Mil', 'event': '100 Player Rumble'}, 
	1040975933772931172: {'prize': '3 MIl', 'event': 'Daily Rumble'},
	1042408506181025842: {'prize': '10 Mil', 'event': 'Weekly Rumble'},
}	

class Payout(commands.GroupCog, name="payout", description="Payout commands"):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.mongo['Payout_System']
        self.bot.payout_config = Document(self.db, "payout_config")
        self.bot.payout_queue = Document(self.db, "payout_queue")
        self.bot.payout_pending = Document(self.db, "payout_pending")
        self.bot.payout_delete_queue = Document(self.db, "payout_delete_queue")
        self.claim_task = self.check_unclaim.start()
        self.delete_queue_task = self.check_delete_queue.start()

    def cog_unload(self):
        self.claim_task.cancel()
        self.delete_queue_task.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(Payout_Buttton())
        self.bot.add_view(Payout_claim())

    @tasks.loop(seconds=10)
    async def check_unclaim(self):
        data = await self.bot.payout_queue.get_all()
        for payout in data:
            now = datetime.datetime.utcnow()
            if now > payout['queued_at'] + datetime.timedelta(seconds=payout['claim_time']):
                view = discord.ui.View()
                view.add_item(discord.ui.Button(label="Claim period expired!", style=discord.ButtonStyle.gray, disabled=True, emoji="<a:nat_cross:1010969491347357717>"))
                payout_config = await self.bot.payout_config.find(payout['guild'])
                guild = self.bot.get_guild(payout['guild'])
                channel = guild.get_channel(payout_config['pending_channel'])
                try:
                    message = await channel.fetch_message(payout['_id'])
                except discord.NotFound:
                    continue
                embed = message.embeds[0]
                embed.title = "Payout Expired"
                embed.description = embed.description.replace("`Pending`", "`Expired`")
                await message.edit(embed=embed,view=view, content=f"<@{payout['winner']}> you have not claimed your payout in time.")
                host = guild.get_member(payout['set_by'])
                dm_view = discord.ui.View()
                dm_view.add_item(discord.ui.Button(label="Payout Message Link", style=discord.ButtonStyle.url, url=message.jump_url))
                user = guild.get_member(payout['winner'])
                self.bot.dispatch("payout_expired", message, user)
                delete_queue_data = {'_id': message.id,'channel': message.channel.id,'now': datetime.datetime.utcnow(),'delete_after': 1800, 'reason': 'payout_expired'}
                await self.bot.payout_delete_queue.insert(delete_queue_data)
                try:
                    await host.send(f"<@{payout['winner']}> has failed to claim within the deadline. Please reroll/rehost the event/giveaway.", view=dm_view)
                except discord.HTTPException:
                    pass
                await self.bot.payout_queue.delete(payout['_id'])
            else:
                pass
    
    @tasks.loop(seconds=10)
    async def check_delete_queue(self):
        data = await self.bot.payout_delete_queue.get_all()
        now = datetime.datetime.utcnow()
        for payout in data:
            if payout['reason'] == 'payout_expired': continue
            if now > payout['now'] + datetime.timedelta(seconds=payout['delete_after']):
                channel = self.bot.get_channel(payout['channel'])
                try:
                    message = await channel.fetch_message(payout['_id'])
                except discord.NotFound:
                    continue
                #await message.delete()
                await self.bot.payout_delete_queue.delete(payout['_id'])
            else:
                pass
    
    @check_delete_queue.before_loop
    async def before_check_delete_queue(self):
        await self.bot.wait_until_ready()
            
    @check_unclaim.before_loop
    async def before_check_unclaim(self):
        await self.bot.wait_until_ready()
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild is None or message.guild.id != 785839283847954433: return
        if not message.author.bot: return
        if message.author.id != 693167035068317736: return
        if message.channel.id not in auto_payout.keys(): return
        if len(message.embeds) == 0: return

        embed = message.embeds[0]
        if embed.title != "<:Crwn2:872850260756664350> **__WINNER!__**" and len(message.mentions) == 1:
            return
        if len(message.mentions) == 0: return
        winner = message.mentions[0]
        prize = auto_payout[message.channel.id]['prize']
        event = auto_payout[message.channel.id]['event']
        data = await self.bot.payout_config.find(message.guild.id)
        claim_time = data['default_claim_time'] if data['default_claim_time'] is not None else 86400
        claim_timestamp = f"<t:{round((datetime.datetime.now() + datetime.timedelta(seconds=claim_time)).timestamp())}:R>"

        embed = discord.Embed(title="Payout Queued", color=self.bot.default_color, timestamp=datetime.datetime.now(), description="")
        embed.description += f"**Event:** {event}\n"
        embed.description += f"**Winner:** {winner.mention} ({winner.name}#{winner.discriminator})\n"
        embed.description += f"**Prize:** {prize}\n"
        embed.description += f"**Channel:** {message.channel.mention}\n"
        embed.description += f"**Message:** [Jump to Message]({message.jump_url})\n"
        embed.description += f"**Claim Time:** {claim_timestamp}\n"
        embed.description += f"**Set By:** AutoMatic Payout Queue System\n"
        embed.description += f"**Status:** `Pending`\n"

        pendin_channel = message.guild.get_channel(data['pending_channel'])
        if pendin_channel is None:return
        msg = await pendin_channel.send(f"<@{winner.id}> you have won {prize} in {event}! Please claim your prize within {claim_timestamp} by clicking the button below.", embed=embed, view=Payout_claim())
        queue_data = {
            '_id': msg.id,
            'channel': message.channel.id,
            'guild': message.guild.id,
            'event': event,
            'winner': winner.id,
            'prize': prize,
            'claimed': False,
            'set_by': "AutoMatic Payout Queue System",
            'winner_message_id': message.id,
            'queued_at': datetime.datetime.utcnow(),
            'claim_time': claim_time or 3600,
        }
        await self.bot.payout_queue.insert(queue_data)
        loading_emoji = await self.bot.emoji_server.fetch_emoji(998834454292344842)
        try:
            await message.add_reaction(loading_emoji)
        except discord.HTTPException:
            pass

        await message.channel.send(f"{winner.mention}, your prize has been queued for claim! Please check {pendin_channel.mention} to claim your prize.")
        self.bot.dispatch("payout_queue", message.guild.me, f"{auto_payout[message.channel.id]['event']}", message, msg, winner, auto_payout[message.channel.id]['prize'])
    @app_commands.command(name="set", description="configur the payout system settings")
    @app_commands.describe(event="event name", message_id="winner message id", winners="winner of the event", prize="what did they win?")
    async def payout_set(self, interaction: discord.Interaction, event: str, message_id: str, winners: app_commands.Transform[discord.Member, MultipleMember], prize: str, claim_time: app_commands.Transform[int, TimeConverter]= None):
        data = await self.bot.payout_config.find(interaction.guild.id)
        user_roles = [role.id for role in interaction.user.roles]
        if (set(user_roles) & set(data['event_manager_roles'])):
            pass
        else:
            return await interaction.response.send_message("You are not allowed to use this command!", ephemeral=True)
        
        if claim_time is not None:
            if claim_time < 3600:
                return await interaction.response.send_message("Claim time must be at least 1 hour!", ephemeral=True)

        loading_embed = discord.Embed(description=f"<a:loading:998834454292344842> | Setting up the payout for total of `{len(winners)}` winners!")
        finished_embed = discord.Embed(description=f"")        
        await interaction.response.send_message(embed=loading_embed, ephemeral=True)
        loading_emoji = await self.bot.emoji_server.fetch_emoji(998834454292344842)

        try:
            winner_message = await interaction.channel.fetch_message(message_id)
            await winner_message.add_reaction(loading_emoji)
        except discord.NotFound:
            await interaction.followup.send("I could not find that message! Please make sure the message is in this channel!", ephemeral=True)
            return
        
        data = await self.bot.payout_config.find(interaction.guild.id)
        if data is None:
            data = {
                '_id': interaction.guild.id,
                'queue_channel': None,
                'pending_channel': None,
                'manager_roles': [],
                'log_channel': None,
            }
            await self.bot.payout_config.insert(data)
            return await interaction.followup.send("Please set up the payout config first!", ephemeral=True)
        
        if data['pending_channel'] is None:
            return await interaction.followup.send("Please set up the payout config first!", ephemeral=True)
        
        queue_channel = interaction.guild.get_channel(data['pending_channel'])
        if queue_channel is None:
            return await interaction.followup.send("Please set up the payout config first!", ephemeral=True)
        claim_time = claim_time if claim_time != None else data['default_claim_time']
        claim_timestamp = f"<t:{round((datetime.datetime.now() + datetime.timedelta(seconds=claim_time)).timestamp())}:R>"
        first_message = None
        for winner in winners:
            if isinstance(winner, discord.Member):
                embed = discord.Embed(title="Payout Queued", color=self.bot.default_color, timestamp=datetime.datetime.now(), description="")
                embed.description += f"**Event:** {event}\n"
                embed.description += f"**Winner:** {winner.mention} ({winner.name}#{winner.discriminator})\n"
                embed.description += f"**Prize:** {prize}\n"
                embed.description += f"**Channel:** {winner_message.channel.mention}\n"
                embed.description += f"**Message:** [Jump to Message]({winner_message.jump_url})\n"
                embed.description += f"**Claim Time:** {claim_timestamp}\n"
                embed.description += f"**Set By:** {interaction.user.mention}\n"
                embed.description += f"**Status:** `Pending`\n"

                msg = await queue_channel.send(embed=embed, content=f"{winner.mention}, please claim your prize within the next {claim_timestamp}!\n> If not claimed within the deadline, you are liable to be rerolled/rehosted.", view=Payout_claim())
                if first_message is None: first_message = msg
                data = {
					'_id': msg.id,
					'channel': winner_message.channel.id,
					'guild': interaction.guild.id,
					'event': event,
					'winner': winner.id,
					'prize': prize,
                    'claimed': False,
					'set_by': interaction.user.id,
					'winner_message_id': winner_message.id,
                    'queued_at': datetime.datetime.utcnow(),
                    'claim_time': claim_time or 3600,
				}
                try:
                    await self.bot.payout_queue.insert(data)
                    loading_embed.description += f"\n <:octane_yes:1019957051721535618> | Payout Successfully queued for {winner.mention} ({winner.name}#{winner.discriminator})"
                    finished_embed.description += f"\n <:octane_yes:1019957051721535618> | Payout Successfully queued for {winner.mention} ({winner.name}#{winner.discriminator})"

                except Exception as e:

                    loading_embed.description += f"\n <:dynoError:1000351802702692442> | Failed to queue payout for {winner.mention} ({winner.name}#{winner.discriminator})"
                    finished_embed.description += f"\n <:dynoError:1000351802702692442> | Failed to queue payout for {winner.mention} ({winner.name}#{winner.discriminator})"
                
                await interaction.edit_original_response(embed=loading_embed)
                await asyncio.sleep(1)
                self.bot.dispatch("payout_queue", interaction.user, event, winner_message, msg, winner, prize)

        if first_message is None:
            return await interaction.edit_original_response("No valid winners were found!", embed=None)
        link_view = discord.ui.View()
        link_view.add_item(discord.ui.Button(label="Go to Payout-Queue", url=first_message.jump_url))
        finished_embed.description += f"\n**<:nat_reply_cont:1011501118163013634> Successfully queued {len(winners)}**"
        await interaction.edit_original_response(embed=finished_embed, view=link_view)
    
    @app_commands.command(name="clear-expired", description="Clears all expired payouts from the queue")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def clear_expired(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=discord.Embed(color=self.bot.default_color, description="clearing expired payouts..."), ephemeral=False)
        deleted = 0
        delete_queue =  await self.bot.payout_delete_queue.get_all()
        config = await self.bot.payout_config.find(interaction.guild.id)

        queue_channel = interaction.guild.get_channel(config['pending_channel'])
        for data in delete_queue:
            if data['reason'] == "payout_claim": continue
            try:
                msg = await queue_channel.fetch_message(data['_id'])
                await msg.delete()
                deleted += 1
            except:
                pass
            await self.bot.payout_delete_queue.delete(data['_id'])
        await interaction.edit_original_response(embed=discord.Embed(color=self.bot.default_color, description=f"Successfully deleted {deleted} expired payouts!"))
    
    @commands.Cog.listener()
    async def on_payout_queue(self, host: discord.Member,event: str, win_message: discord.Message, queue_message: discord.Message, winner: discord.Member, prize: str):
        embed = discord.Embed(title="Payout | Queued", color=discord.Color.green(), timestamp=datetime.datetime.now(), description="")
        embed.description += f"**Host:** {host.mention}\n"
        embed.description += f"**Event:** {event}\n"
        embed.description += f"**Winner:** {winner.mention} ({winner.name}#{winner.discriminator})\n"
        embed.description += f"**Prize:** {prize}\n"
        embed.description += f"**Event Message:** [Jump to Message]({win_message.jump_url})\n"
        embed.description += f"**Queue Message:** [Jump to Message]({queue_message.jump_url})\n"
        embed.set_footer(text=f"Queue Message ID: {queue_message.id}")

        config = await self.bot.payout_config.find(queue_message.guild.id)
        if config is None: return
        log_channel = queue_message.guild.get_channel(config['log_channel'])
        if log_channel is None: return
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_payout_claim(self, message: discord.Message, user: discord.Member):
        embed = discord.Embed(title="Payout | Claimed", color=discord.Color.green(), timestamp=datetime.datetime.now(), description="")
        embed.description += f"**User:** {user.mention}\n"
        embed.description += f"**Queue Message:** [Jump to Message]({message.jump_url})\n"
        embed.set_footer(text=f"Queue Message ID: {message.id}")

        config = await self.bot.payout_config.find(message.guild.id)
        if config is None: return
        log_channel = message.guild.get_channel(config['log_channel'])
        if log_channel is None: return
        await log_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_payout_pending(self, message: discord.Message):
        embed = discord.Embed(title="Payout | Pending", color=discord.Color.yellow(), timestamp=datetime.datetime.now(), description="")
        embed.description += f"**Queue Message:** [Jump to Message]({message.jump_url})\n"
        embed.set_footer(text=f"Queue Message ID: {message.id}")

        config = await self.bot.payout_config.find(message.guild.id)
        if config is None: return
        log_channel = message.guild.get_channel(config['log_channel'])
        if log_channel is None: return
        await log_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_payout_paid(self, message: discord.Message, user: discord.Member, winner: discord.Member, prize: str):
        embed = discord.Embed(title="Payout | Paid", color=discord.Color.dark_green(), timestamp=datetime.datetime.now(), description="")
        embed.description += f"**User:** {user.mention}\n"
        embed.description += f"**Winner:** {winner.mention} ({winner.name}#{winner.discriminator})\n"
        embed.description += f"**Prize:** {prize}\n"
        embed.description += f"**Queue Message:** [Jump to Message]({message.jump_url})\n"
        embed.set_footer(text=f"Queue Message ID: {message.id}")

        config = await self.bot.payout_config.find(message.guild.id)
        if config is None: return
        log_channel = message.guild.get_channel(config['log_channel'])
        if log_channel is None: return
        await log_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_payout_expired(self, message: discord.Message, user: discord.Member):
        embed = discord.Embed(title="Payout | Expired", color=discord.Color.red(), timestamp=datetime.datetime.now(), description="")
        embed.description += f"**User:** {user.mention}\n"
        embed.description += f"**Queue Message:** [Jump to Message]({message.jump_url})\n"
        embed.set_footer(text=f"Queue Message ID: {message.id}")

        config = await self.bot.payout_config.find(message.guild.id)
        if config is None: return
        log_channel = message.guild.get_channel(config['log_channel'])
        if log_channel is None: return
        await log_channel.send(embed=embed)

class Dump(commands.GroupCog, name="dump", description="Dump commands"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="role", description="Dump a role")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.describe(role="The role to dump")
    async def dump_role(self, interaction: discord.Interaction, role: discord.Role):
        if len(role.members) <= 30:
            msg = ""
            for member in role.members:
                msg += f"{member.name}#{member.discriminator} ({member.id})\n"
            await interaction.response.send_message(msg, ephemeral=False)
        else:
            await interaction.response.send_message("Too many members in the role! creating a file...", ephemeral=False)
            msg = ""
            for member in role.members:
                msg += f"{member.name}#{member.discriminator} ({member.id})\n"
            buffer = BytesIO(msg.encode('utf-8'))
            file = discord.File(buffer, filename=f"{role.name}.txt")
            buffer.close()
            await interaction.edit_original_response(content="Here you go!", attachments=[file])

    @app_commands.command(name="invite", description="dump an invite")
    @app_commands.describe(user="The user to dump the invites from")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def dump_invite(self, interaction: discord.Interaction, user: discord.Member):
        data = await self.bot.invites.find(user.id)
        if data is None:
            return await interaction.response.send_message("User has no invites!", ephemeral=True)

        if len(data['invites']) <= 30:
            msg = ""
            for invite in data['invites']:
                msg += f"{invite}\n"
            await interaction.response.send_message(msg, ephemeral=False)
        else:
            await interaction.response.send_message("Too many invites! creating a file...", ephemeral=False)
            msg = ""
            for invite in data['invites']:
                msg += f"{invite}\n"
            buffer = BytesIO(msg.encode('utf-8'))
            file = discord.File(buffer, filename=f"{user.name}.txt")
            buffer.close()
            await interaction.edit_original_response(content="Here you go!", attachments=[file])

async def setup(bot):
    await bot.add_cog(Payout(bot))
    await bot.add_cog(Dump(bot))
