import asyncio
import discord
import aiohttp
import json
import datetime
from discord.ext import commands, tasks
from discord import Interaction, app_commands
import pandas as pd
from utils.db import Document
from utils.checks import is_dev
from utils.views.buttons import Link_view

class Link_Backend:
	def __init__(self, bot: commands.Bot, Document, auth_link:str):
		self.bot = bot
		self.auth = Document(self.bot.db, "OAuth2")
		self.session = aiohttp.ClientSession()
		self.auth_link = auth_link
		self.base_url = "https://discord.com/api/v10"
	
	async def register(self):
		meta_data = [{"type": 7,"key": "beast","name": "♡੭𓈒 Beast Donor ♡੭𓈒","description": "Top Donor for 8k Celebs"},{"type": 7,"key": "weekly_winner","name": "࿔･ﾟ♛ Weekly Topper ♛ ࿔･ﾟ","description": "Amari Winner"}]
		url = f"{self.base_url}/applications/{self.bot.user.id}/role-connections/metadata"
		headers = {"Authorization": f"Bot {self.bot.token}", "Content-Type": "application/json"}
		response = await self.session.put(url, headers=headers, data=json.dumps(meta_data))
		return response
	
	async def verify(self, user: discord.Member, key: str, value):
		user_data = await self.auth.find(user.id)
		if not user_data:
			user_data = {"_id": user.id, 'access_token': None, 'refresh_token': None, 'metadata': {'platform_name': None, 'platform_username': None, 'metadata': {key: value}},'expires_at': None, 'expires_in': None,'scope': None,'token_type': None, 'username': user.name, 'discriminator': user.discriminator}
			await self.auth.insert(user_data)
			return False

		meta_data = await self.get_metadata(user_data)
		if meta_data.status != 200: return False
		meta_data = await meta_data.json()

		if key not in meta_data['metadata'].keys(): meta_data['metadata'][key] = value
		else: meta_data['metadata'][key] = value

		meta_data['platform_name'] = "The Gambler's Kingdom"
		meta_data['platform_username'] = user.name
		user_data['metadata']['platform_name'] = "The Gambler's Kingdom"
		user_data['metadata']['platform_username'] = user.name

		user_data['metadata'] = meta_data
		await self.auth.update(user_data)

		url = f"{self.base_url}/users/@me/applications/{self.bot.user.id}/role-connection"
		headers = {"Authorization": f"Bearer {user_data['access_token']}", "Content-Type": "application/json"}
		response = await self.session.put(url, headers=headers, data=json.dumps(meta_data))
		return response

	async def get_metadata(self, user_data):
		url = f"{self.base_url}/users/@me/applications/{self.bot.user.id}/role-connection"
		headers = {'Authorization': f"Bearer {user_data['access_token']}"}
		response = await self.session.get(url, headers=headers)
		return response

	async def refresh(self, user: discord.User, user_data:dict):
		url = f"{self.base_url}/oauth2/token"
		headers = {"Content-Type": "application/x-www-form-urlencoded"}
		data = {"client_id": self.bot.user.id,"client_secret": self.bot.secret,"grant_type": "refresh_token","refresh_token": user_data['refresh_token']}
		response = await self.session.post(url, headers=headers, data=data)
		return response

	async def close(self):
		await self.session.close()

utc = datetime.timezone.utc
time = datetime.time(hour=5, minute=00, tzinfo=utc)
class Linked_Roles(commands.GroupCog, name="linkedroles"):   
	def __init__(self, bot):
		self.bot = bot
		self.bot.linked_roles = Link_Backend(self.bot, Document, 'http://tgk-api.vercel.app/api/linked-role/auth')
		self.refresh_task = self.refresh.start()
		self.refresh_progress = False
		self.refresh_beast_donor = self.refresh_beast_donor.start()
	
	def cog_unload(self):
		self.refresh_task.cancel()

	
	@tasks.loop(hours=10)
	async def refresh(self):
		if self.refresh_progress: return
		self.refresh_progress = True

		data = await self.bot.linked_roles.auth.get_all()
		now = datetime.datetime.utcnow()
		for user_data in data:
			if user_data['expires_at'] == None: continue
			if user_data['access_token'] == None: continue
			if user_data['refresh_token'] == None: continue

			if now >= user_data['expires_at']:
				response = await self.bot.linked_roles.refresh(user_data['_id'], user_data)
				if response.status != 200: continue
				response = await response.json()
				user_data['access_token'] = response['access_token']
				user_data['refresh_token'] = response['refresh_token']
				user_data['expires_at'] = datetime.datetime.utcnow() + datetime.timedelta(seconds=response['expires_in'])
				user_data['expires_in'] = response['expires_in']
				user_data['scope'] = response['scope']
				user_data['token_type'] = response['token_type']
				await self.bot.linked_roles.auth.update(user_data)
		self.refresh_progress = False
	
	@refresh.before_loop
	async def before_refresh(self):
		await self.bot.wait_until_ready()
	
	@tasks.loop(time=time)
	async def refresh_beast_donor(self):
		gk = self.bot.get_guild(785839283847954433)
		beast_role = gk.get_role(821052747268358184)

		log_channel = gk.get_channel(999575712736497695)
		leaderboard_channel = gk.get_channel(1094701054232375376)

		data = await self.bot.donorBank.find_many_by_custom( {"event" : { "$elemMatch": { "name": '8k',"bal":{"$gt":0} }}})
		df = pd.DataFrame(data)
		df['8k']  = df.event.apply(lambda x: x[-1]['bal'])
		df = df.drop(['bal','grinder_record','event'], axis=1)
		df = df.sort_values(by='8k',ascending=False)
		top_3 = df.head(3)

		for user in beast_role.members:
			if user.id not in top_3['_id'].values:
				# code to deassign role
				new_medata = await self.bot.linked_roles.verify(user, 'beast', 0)
				if isinstance(new_medata, bool):
					await log_channel.send(embed=discord.Embed(description=f"{user.mention}(ID: `{user.id}`) have not connected their account yet, please ask them to connect and changes will be applied automatically", color=0x2b2d31))
					continue
				new_medata = await new_medata.json()
				if 'code' in new_medata.keys():
					await log_channel.send(embed=discord.Embed(description=f"Failed to verify role connection for {user.mention}: \n```json\n{new_medata}\n```", color=0x2b2d31))           
				else:
					await log_channel.send(embed=discord.Embed(description=f"Successfully removed {user.mention}'s {beast_role.mention}", color=0x2b2d31))
		
		for index in top_3.index:
			user = gk.get_member(top_3['_id'][index])
			if user == None: continue
			if beast_role not in user.roles:
				# code to assign role
				new_medata = await self.bot.linked_roles.verify(user, 'beast', 1)
				
				embed = discord.Embed(
					title="Congratulations Beast Donor!",
					description=f"<a:tgk_redheart:1005361530122022922> Check Leaderboard [`here`]({(await leaderboard_channel.fetch_message(leaderboard_channel.last_message_id)).jump_url}) .\n"
								f"<a:tgk_redheart:1005361530122022922> **Grab role:** `server settings > linked roles`.\n"
								f"<a:tgk_redheart:1005361530122022922> Reach out to <#785901543349551104> for any queries.\n"
								f"<a:tgk_redheart:1005361530122022922> [`Perks`](https://discord.com/channels/785839283847954433/1094511770514755584/1094524085289111593) are claimable after <#1051387593318740009> closes.\n", 
					color=0x2b2d31,
					timestamp=datetime.datetime.utcnow()
				)
				embed.set_footer(text="Thank you for supporting TGK")

				if isinstance(new_medata, bool):
					await log_channel.send(embed=discord.Embed(description=f"{user.mention}(ID: `{user.id}`) have not connected their account yet, please ask them to connect and changes will be applied automatically", color=0x2b2d31))
					continue
				new_medata = await new_medata.json()
				await log_channel.send(embed=discord.Embed(description=f"Meta data for {user.mention}: \n```json\n{new_medata}\n```", color=0x2b2d31))
				if 'code' in new_medata.keys():
					await log_channel.send(embed=discord.Embed(description=f"Failed to verify role connection for {user.mention}: \n```json\n{new_medata}\n```", color=0x2b2d31))
				else:
					try:
						await user.send(embed=embed)
						await asyncio.sleep(1)
					except:
						await log_channel.send(content = f'Unable to dm {user.mention}(ID: `{user.id}`)', embed=embed)
		
		
		
	@refresh_beast_donor.before_loop
	async def before_refresh_beast_donor(self):
		await self.bot.wait_until_ready()
	

	@commands.Cog.listener()
	async def on_weekly_leaderboard_reset(self, channel: discord.TextChannel):
		ranks = await self.bot.ranks.get_all()
		metadatas = await self.bot.linked_roles.auth.get_all()
		for metadata in metadatas:
			if metadata['access_token'] == None: continue
			if 'weekly_winner' not in metadata['metadata'].keys(): continue
			else: await self.bot.linked_roles.verify(metadata['_id'], 'weekly_winner', False)
		ranks = sorted(ranks, key=lambda x: x['xp'], reverse=True)
		for i in ranks[:3]:
			user = self.bot.get_user(i['_id'])
			if user == None: continue
			await self.bot.linked_roles.verify(user, 'weekly_winner', True)
		embed = discord.Embed(description="Role connections have been updated for the weekly leaderboard winners!\n", color=0x2b2d31)
		embed.set_footer(text="if any of the winners have not connected their account you can do by clicking the link button below.")
		await channel.send(embed=embed, view=Link_view(label="Link Account", url=self.bot.linked_roles.auth_link))

		#for i in ranks: await self.bot.ranks.delete(i['_id'])
	
	@app_commands.command(name="register", description="Register/refresh a role connection metadata")
	@app_commands.check(is_dev)
	async def register(self, interaction: Interaction):
		await interaction.response.send_message(embed=discord.Embed(description="Registering role connection metadata...", color=0x2b2d31))
		new_medata = await self.bot.linked_roles.register()
		new_medata = await new_medata.json()
		if 'errors' or 'message' in new_medata.keys():
			embed = discord.Embed(description=f"Failed to register role connection metadata: \n```json\n{new_medata}\n```", color=0x2b2d31)
		embed = discord.Embed(title="New Role Connection Metadata", description="", color=0x2b2d31)
		for role in new_medata:
			embed.description += f"**Name:** {role['name']}\n**Description:** {role['description']}\n**Key:** {role['key']}\n\n"
		await interaction.edit_original_response(embed=embed)
	
	@app_commands.command(name="show", description="Show a role connection metadata")
	@app_commands.check(is_dev)
	async def show(self, interaction: Interaction, member: discord.Member):
		user_data = await self.bot.linked_roles.auth.find(member.id)
		if not user_data:
			await interaction.response.send_message(embed=discord.Embed(description="User is not registered", color=0x2b2d31))
			return
		if not user_data['access_token']:
			await interaction.response.send_message(embed=discord.Embed(description="User is not linked", color=0x2b2d31))
			return
		await interaction.response.send_message(embed=discord.Embed(description="Fetching role connection metadata...", color=0x2b2d31))
		new_metata = await self.bot.linked_roles.get_metadata(user_data)
		new_metata = await new_metata.json()
		if 'message' or 'code' in new_metata.keys():
			embed = discord.Embed(description=f"Failed to fetch role connection metadata: \n```json\n{new_metata}\n```", color=0x2b2d31)
		embed = discord.Embed(title="Role Connection Metadata", description="", color=0x2b2d31)
		embed.description += f"**Platform Name:** {new_metata['platform_name']}\n**Platform Username:** {new_metata['platform_username']}\n"
		value = ""
		for meta in new_metata['metadata'].keys():
			value += f"**Name: **{meta}\n**Value: **{new_metata['metadata'][meta]}\n\n"
		embed.add_field(name="Metadata", value=value)
		await interaction.edit_original_response(embed=embed)

	@app_commands.command(name="update", description="Verify a role connection manually")
	@app_commands.checks.has_permissions(manage_guild=True)
	@app_commands.describe(key="Select a connection key", value="Select a connection value")
	@app_commands.choices(key=[app_commands.Choice(name="Beast Donor", value="beast"), app_commands.Choice(name="Weekly Winner", value="wamari")],value=[app_commands.Choice(name="True", value=1), app_commands.Choice(name="False", value=0)])
	async def verify(self, interaction: Interaction, user: discord.User, key: app_commands.Choice[str], value: app_commands.Choice[int]):
		await interaction.response.send_message(embed=discord.Embed(description="Verifying role connection...", color=0x2b2d31))
		new_medata = await self.bot.linked_roles.verify(user, key.value, value.value)
		if new_medata not in [None,False,True]:
			return await interaction.edit_original_response(embed=discord.Embed(description=f"User have not connected their account yet, please ask them to connect their and changes will be applied automatically\n```\npy\n{new_medata}\n```", color=0x2b2d31))
		new_medata = await new_medata.json()
		if 'code' in new_medata.keys():
			await interaction.edit_original_response(embed=discord.Embed(description=f"Failed to verify role connection: \n```json\n{new_medata}\n```", color=0x2b2d31))           
		else:
			await interaction.edit_original_response(embed=discord.Embed(description=f"Successfully updated {user.mention}'s role connection for {key.name}", color=0x2b2d31))

async def setup(bot):
	await bot.add_cog(Linked_Roles(bot))
