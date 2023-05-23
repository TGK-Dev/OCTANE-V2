import discord
import datetime
import asyncio
import humanfriendly
from discord import app_commands
from discord.ext import commands, tasks
import pandas as pd
from utils.db import Document
from utils.views.payout_system import Payout_Config_Edit
from utils.transformer import MultipleMember
from utils.views.payout_system import Payout_Buttton, Payout_claim
from utils.transformer import TimeConverter
from typing import Literal, List
from io import BytesIO
from typing import Union
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageChops

auto_payout = {
	1040975933772931172: {'prize': '10 MIl', 'event': 'Daily Rumble'},
	1042408506181025842: {'prize': '25 Mil', 'event': 'Weekly Rumble'},
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
		self.comman_event = ["Mega Giveaway", "Daily Giveaway", "Silent Giveaway", "Black Tea", "Rumble Royale", "Hunger Games", "Guess The Number", "Split Or Steal"]
	
	async def event_auto_complete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
		_list = [
			app_commands.Choice(name=event, value=event)
			for event in self.comman_event if event.lower() in current.lower()
		]
		if len(_list) == 0:
			return [
				app_commands.Choice(name=event, value=event)
				for event in self.comman_event
			]
		return _list[:24]

	async def item_autocomplete(self, interaction: discord.Interaction, string: str) -> List[app_commands.Choice[str]]:
		choices = []
		for item in self.bot.dank_items_cache.keys():
			if string.lower() in item.lower():
				choices.append(app_commands.Choice(name=item, value=item))
		if len(choices) == 0:
			return [
				app_commands.Choice(name=item, value=item)
				for item in self.bot.dank_items_cache.keys()
			]
		else:
			return choices[:24]
	
	async def create_pending_embed(self, event: str, winner: discord.Member, prize: str, channel: discord.TextChannel, message: discord.Message, claim_time: int, host: discord.Member, item: str=None) -> discord.Embed:
		embed = discord.Embed(title="Payout Queue", timestamp=datetime.datetime.now(), description="", color=self.bot.default_color)
		embed.description += f"**Event:** {event}\n"
		embed.description += f"**Winner:** {winner.mention}\n"
		if item:
			embed.description += f"**Prize:** {prize} x {item}\n"
		else:
			embed.description += f"**Prize:** {prize}\n"
		embed.description += f"**Channel:** {channel.mention}\n"
		embed.description += f"**Message:** [Click Here]({message.jump_url})\n"
		embed.description += f"**Claim Time:** <t:{claim_time}:R> (<t:{claim_time}:T>)\n"
		embed.description += f"**Set By:** {host.mention}\n"
		embed.description += f"**Status:** `Pending`"
		embed.set_footer(text=f"ID: {message.id}")

		return embed
			

	def cog_unload(self):
		self.claim_task.cancel()

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

				event_channel = guild.get_channel(payout['channel'])
				try:
					event_message = await event_channel.fetch_message(payout['winner_message_id'])
					loading_emoji = await self.bot.emoji_server.fetch_emoji(998834454292344842)
					await event_message.remove_reaction(loading_emoji, event_message.guild.me)
				except discord.NotFound:
					pass

				self.bot.dispatch("payout_expired", message, user)
				delete_queue_data = {'_id': message.id,'channel': message.channel.id,'now': datetime.datetime.utcnow(),'delete_after': 1800, 'reason': 'payout_expired'}
				if host:
					try:
						await host.send(f"<@{payout['winner']}> has failed to claim within the deadline. Please reroll/rehost the event/giveaway.", view=dm_view)
					except discord.HTTPException:
						pass

				await self.bot.payout_queue.delete(payout['_id'])
			else:
				pass

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

		await message.channel.send(f"{winner.mention}, your prize {prize} has been queued for payout. Please check <#{data['pending_channel']}> for more information.", allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False))
		self.bot.dispatch("payout_queue", message.guild.me, f"{auto_payout[message.channel.id]['event']}", message, msg, winner, auto_payout[message.channel.id]['prize'])

	@app_commands.command(name="set", description="configur the payout system settings")
	@app_commands.describe(event="event name", message_id="winner message id", winners="winner of the event", quantity='A constant number like "123" or a shorthand like "5m"', item="what item did they win?")#, claim_time="how long do they have to claim their prize?")
	@app_commands.autocomplete(event=event_auto_complete)
	@app_commands.autocomplete(item=item_autocomplete)
	async def payout_set(self, interaction: discord.Interaction, event: str, message_id: str, winners: app_commands.Transform[discord.Member, MultipleMember], quantity: str, item: str=None):
		data = await self.bot.payout_config.find(interaction.guild.id)
		if data is None: return await interaction.response.send_message("Payout system is not configured yet!", ephemeral=True)
		user_roles = [role.id for role in interaction.user.roles]
		if (set(user_roles) & set(data['event_manager_roles'])):
			pass
		else:
			return await interaction.response.send_message("You are not allowed to use this command!", ephemeral=True)
		
		try:
			prize = quantity.lower()
			prize = prize.replace("k", "e3",100)
			prize = prize.replace("m", "e6",100)
			prize = prize.replace(" mil", "e6",100)
			prize = prize.replace("mil", "e6",100)
			prize = prize.replace("b", "e9",100)
			prize = int(float(prize))
		except:
			return await interaction.response.send_message(content="Incorrect amount mentioned.", ephemeral=True)
		
		claim_time = data['default_claim_time']

		loading_embed = discord.Embed(description=f"<a:loading:998834454292344842> | Setting up the payout for total of `{len(winners)}` winners!")
		finished_embed = discord.Embed(description=f"")

		await interaction.response.send_message(embed=loading_embed, ephemeral=True)
		loading_emoji = await self.bot.emoji_server.fetch_emoji(998834454292344842)

		try:
			winner_message = await interaction.channel.fetch_message(message_id)
			await winner_message.add_reaction(loading_emoji)
		except:
			await interaction.edit_original_response(embed=discord.Embed(description=f"Could not find the winner message. Please make sure you have the correct message id and same channel as the winner message.", color=self.bot.error_color))
		
		queue_channel = interaction.guild.get_channel(data['pending_channel'])
		if queue_channel is None:
			await interaction.edit_original_response(embed=discord.Embed(description=f"Could not find the queue channel. Please make sure you have the correct channel config.", color=self.bot.error_color))
		
		claim_time_time = round((datetime.datetime.now() + datetime.timedelta(seconds=claim_time)).timestamp())
		first_message = False
		first_url = None
		for winner in winners:
			if isinstance(winner, discord.Member):
				embed = await self.create_pending_embed(event, winner, prize, winner_message.channel, winner_message, claim_time_time, interaction.user, item)
				msg = await queue_channel.send(f"<@{winner.id}> you have won {prize} in {event}! Please claim your prize within <t:{claim_time}:r> by clicking the button below.", embed=embed, view=Payout_claim())
				if first_message is False:					
					first_message = True
					first_url = msg.jump_url
				
				payout_data = {
					"_id": msg.id,
					"channel": winner_message.channel.id,
					"guild": msg.guild.id,
					"winner": winner.id,
					"prize": prize,
					"event": event,
					"item": item if item else None,
					"claimed": False,
					"set_by": interaction.user.id,
					"winner_message_id": winner_message.id,
					"queued_at": datetime.datetime.now(),
					"claim_time": claim_time
				}
				try:
					await self.bot.payout_queue.insert(payout_data)
					loading_embed.description += f"\n <:octane_yes:1019957051721535618> | Payout Successfully queued for {winner.mention} ({winner.name}#{winner.discriminator})"
					finished_embed.description += f"\n <:octane_yes:1019957051721535618> | Payout Successfully queued for {winner.mention} ({winner.name}#{winner.discriminator})"

				except Exception as e:
					loading_embed.description += f"\n <:dynoError:1000351802702692442> | Failed to queue payout for {winner.mention} ({winner.name}#{winner.discriminator})"
					finished_embed.description += f"\n <:dynoError:1000351802702692442> | Failed to queue payout for {winner.mention} ({winner.name}#{winner.discriminator})"
				
				await interaction.edit_original_response(embed=loading_embed)
				await asyncio.sleep(0.75)
				self.bot.dispatch("payout_queue", interaction.user, event, winner_message, msg, winner, prize)
		
		link_view = discord.ui.View()
		link_view.add_item(discord.ui.Button(label="View First Payout", url=first_url, style=discord.ButtonStyle.link))
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

utc = datetime.timezone.utc
time = datetime.time(hour=4, minute=30, tzinfo=utc)

class donation(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.db2 = bot.aceDb["TGK"]
		self.bot.donorBank = Document(self.db2, "donorBank")
		# self.celeb_lb = self.celeb_lb.start()

	def cog_unload(self):
		self.celeb_lb.cancel()

	
	# @tasks.loop(time=time)
	# async def celeb_lb(self):
	# 	gk = self.bot.get_guild(785839283847954433)
	# 	leaderboard_channel = gk.get_channel(1094701054232375376)

	# 	if leaderboard_channel is None: 
	# 		return

	# 	data = await self.bot.donorBank.find_many_by_custom( {"event" : { "$elemMatch": { "name": '8k',"bal":{"$gt":0} }}})
	# 	df = pd.DataFrame(data)
	# 	df['8k']  = df.event.apply(lambda x: x[-1]['bal'])
	# 	df = df.drop(['bal','grinder_record','event'], axis=1)
	# 	df = df.sort_values(by='8k',ascending=False)
	# 	top_3 = df.head(3)

	# 	leaderboard = []
	# 	for index in top_3.index:
	# 		user = gk.get_member(top_3['_id'][index])
	# 		leaderboard.append({'user': user,'name': top_3['name'][index],'donated': top_3['8k'][index]}) 
		
	# 	image = await self.create_winner_card(gk, "🎊 8K Celeb's LB 🎊", leaderboard)

	# 	with BytesIO() as image_binary:
	# 		image.save(image_binary, 'PNG')
	# 		image_binary.seek(0)
	# 		await leaderboard_channel.send(file=discord.File(fp=image_binary, filename=f'{gk.name}_celeb_lb_card.png'))
	# 		image_binary.close()
		
	# @celeb_lb.before_loop
	# async def before_celeb_lb(self):
	# 	await self.bot.wait_until_ready()
	
	async def round_pfp(self, pfp: Union[discord.Member, discord.Guild]):
		if isinstance(pfp, discord.Member):
			if pfp.avatar is None:
				pfp = pfp.default_avatar.with_format("png")
			else:
				pfp = pfp.avatar.with_format("png")
		else:
			pfp = pfp.icon.with_format("png")

		pfp = BytesIO(await pfp.read())
		pfp = Image.open(pfp)
		pfp = pfp.resize((95, 95), Image.Resampling.LANCZOS).convert('RGBA')

		bigzise = (pfp.size[0] * 3, pfp.size[1] * 3)
		mask = Image.new('L', bigzise, 0)
		draw = ImageDraw.Draw(mask)
		draw.ellipse((0, 0) + bigzise, fill=255)
		mask = mask.resize(pfp.size, Image.Resampling.LANCZOS)
		mask = ImageChops.darker(mask, pfp.split()[-1])
		pfp.putalpha(mask)

		return pfp

	async def create_winner_card(self, guild: discord.Guild, event_name:str, data: list):
		template = Image.open('./assets/leaderboard_template.png')
		guild_icon = await self.round_pfp(guild)
		template.paste(guild_icon, (15, 8), guild_icon)

		draw = ImageDraw.Draw(template)
		font = ImageFont.truetype('./assets/fonts/DejaVuSans.ttf', 24)
		winner_name_font = ImageFont.truetype('./assets/fonts/Symbola.ttf', 28)
		winner_exp_font = ImageFont.truetype('./assets/fonts/DejaVuSans.ttf', 20)

		winne_postions = {
			#postions of the winners, pfp and name and donation
			0: {'icon': (58, 150), 'name': (176, 165), 'donated': (176, 202)},
			1: {'icon': (58, 265), 'name': (176, 273), 'donated': (176, 309)},
			2: {'icon': (58, 380), 'name': (176, 392), 'donated': (176, 428)}}

		draw.text((135, 28), f"{event_name}", font=winner_name_font, fill="#9A9BD5") #guild name 
		draw.text((135, 61), f"Gambler's Kingdom", font=font, fill="#9A9BD5") #event name

		for i in data[:3]:
			user = i['user']
			index = data.index(i)
			user_icon = await self.round_pfp(user)
			template.paste(user_icon, winne_postions[index]['icon'], user_icon)
			draw.text(winne_postions[index]['name'], f"👑 | {i['name']}", font=winner_name_font, fill="#9A9BD5")
			draw.text(winne_postions[index]['donated'], f"⏣ {i['donated']:,}", font=winner_exp_font, fill="#A8A8C8")

		return template
	
	@app_commands.command(name="celeb-lb", description="Celeb Leaderboard 📈")
	async def _leaderboard(self, interaction: discord.Interaction):
		await interaction.response.defer(thinking=True, ephemeral=False)

		data = await self.bot.donorBank.find_many_by_custom( {"event" : { "$elemMatch": { "name": '8k',"bal":{"$gt":0} }}})
		df = pd.DataFrame(data)
		df['8k']  = df.event.apply(lambda x: x[-1]['bal'])
		df = df.drop(['bal','grinder_record','event'], axis=1)
		df = df.sort_values(by='8k',ascending=False)
		top_3 = df.head(3)

		leaderboard = []
		for index in top_3.index:
			user = interaction.guild.get_member(top_3['_id'][index])
			leaderboard.append({'user': user,'name': top_3['name'][index],'donated': top_3['8k'][index]}) 
		
		image = await self.create_winner_card(interaction.guild, "🎊 8K Celeb's LB 🎊", leaderboard)

		with BytesIO() as image_binary:
			image.save(image_binary, 'PNG')
			image_binary.seek(0)
			await interaction.followup.send(file=discord.File(fp=image_binary, filename=f'{interaction.guild.name}_celeb_lb_card.png'))
			image_binary.close()


class Seggestions_db:
	def __init__(self, bot):
		self.db = bot.mongo['Suggestion']
		self.config = Document(self.db, 'config')
		self.suggestions = Document(self.db, 'suggestions')


class Suggestions(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.suggestions = Seggestions_db(bot)

	
	@commands.command(name="suggest", description="Suggest something for the server")
	async def _suggest(self, ctx: commands.Context, *, suggestion: str):
		config = await self.suggestions.config.find(ctx.guild.id)
		if config is None:
			return await ctx.send("Suggestions are disabled in this server")
		if config['channel'] is None:
			return await ctx.send("Suggestions are disabled in this server")
		channel = ctx.guild.get_channel(config['channel'])
		if channel is None:
			return await ctx.send("Suggestions are disabled in this server")
		
		embed = discord.Embed(title=f"Suggestion #{config['count']}", description=suggestion, color=discord.Color.blurple())
		embed.set_author(name=ctx.author, icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar)
		embed.set_footer(text=f"ID: {ctx.author.id}")
		msg = await channel.send(embed=embed)
		await msg.add_reaction('<a:ace_upvote:1004650954118942812>')
		await msg.add_reaction('<a:ace_downvote:1004651017427755058>')
		data = {
			'_id': config['count'],
			'author': ctx.author.id,
			'channel': channel.id,
			'message': msg.id,
			'suggestion': suggestion,
			'status': 'pending'
		}
		await self.suggestions.suggestions.insert(data)
		config['count'] += 1
		await self.suggestions.config.update(config)

		await ctx.send("Suggestion sent successfully")
		await ctx.message.delete()
		await msg.create_thread(name=f"Suggestion #{config['count']}", auto_archive_duration=1440)

	@commands.command(name="deny", description="Deny a suggestion")
	@commands.has_permissions(manage_guild=True)
	async def _deny(self, ctx: commands.Context, id: int, *, reason: str):

		data = await self.suggestions.suggestions.find(id)
		if data is None:
			return await ctx.send("Invalid suggestion id")
		if data['status'] != 'pending':
			return await ctx.send("This suggestion is already processed")
		
		channel = ctx.guild.get_channel(data['channel'])
		if channel is None:
			return await ctx.send("Invalid suggestion id")
		try:
			msg = await channel.fetch_message(data['message'])
		except discord.NotFound:
			return await ctx.send("Invalid suggestion id")
		
		embed = msg.embeds[0]
		embed.color = discord.Color.red()
		embed.title += " (Denied)"
		embed.add_field(name=f"Reason by {ctx.author.name}", value=reason)

		await msg.edit(embed=embed)
		data['status'] = 'denied'
		await self.suggestions.suggestions.update(data)
		await ctx.send("Suggestion denied successfully")

		author = ctx.guild.get_member(data['author'])
		try:
			await author.send(f"Your suggestion `{data['suggestion']}` was denied by {ctx.author.name} for the following reason:\n{reason}")
		except discord.Forbidden:
			pass

	@commands.command(name="accept", description="Accept a suggestion")
	@commands.has_permissions(manage_guild=True)
	async def _accept(self, ctx: commands.Context, id: int, *, reason: str):
		
		data = await self.suggestions.suggestions.find(id)
		if data is None:
			return await ctx.send("Invalid suggestion id")
		if data['status'] != 'pending':
			return await ctx.send("This suggestion is already processed")
		
		channel = ctx.guild.get_channel(data['channel'])
		if channel is None:
			return await ctx.send("Invalid suggestion id")
		try:
			msg = await channel.fetch_message(data['message'])
		except discord.NotFound:
			return await ctx.send("Invalid suggestion id")
		
		embed = msg.embeds[0]
		embed.color = discord.Color.green()
		embed.title += " (Accepted)"
		embed.add_field(name=f"Reason by {ctx.author.name}", value=reason)

		await msg.edit(embed=embed)
		data['status'] = 'accepted'
		await self.suggestions.suggestions.update(data)
		await ctx.send("Suggestion accepted successfully")

		author = ctx.guild.get_member(data['author'])
		if author is None:
			return
		try:
			await author.send(f"Your #{data['_id']} suggestion has been accepted by {ctx.author.name}.\nReason: {reason}")
		except discord.Forbidden:
			pass
	
	@commands.command(name="suggestion-channel", description="Set the suggestion channel", aliases=['suggestc'])
	@commands.has_permissions(administrator=True)
	async def _suggestion_channel(self, ctx: commands.Context, channel: discord.TextChannel):
		config = await self.suggestions.config.find(ctx.guild.id)
		if config is None:
			config = {
				'_id': ctx.guild.id,
				'channel': None,
				'count': 1
			}
		config['channel'] = channel.id
		await self.suggestions.config.update(config)
		await ctx.send(f"Suggestion channel set to {channel.mention}")

async def setup(bot):
	await bot.add_cog(Payout(bot))
	await bot.add_cog(Suggestions(bot))
	await bot.add_cog(
		donation(bot),
		guilds = [discord.Object(785839283847954433)]
	)
