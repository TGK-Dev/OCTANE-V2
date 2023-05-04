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

class Linked_Roles(commands.GroupCog, name="linkedroles"):
	def __init__(self, bot):
		self.bot = bot
		self.bot.auth = Document(self.bot.db,"OAuth2")
		self.session = aiohttp.ClientSession()
		self.base_url = "https://discord.com/api/v10"
		self.refresh_task = False
		self.auth_refresh = self.refresh_loop.start()
	
	async def get_metadata(self, token: str):
		url = f"{self.base_url}/users/@me/applications/{self.bot.user.id}/role-connection"
		headers = {"Authorization": f"Bearer {token}"}
		response = await self.session.get(url, headers=headers)
		if response.status == 200:
			return await response.json()
		else:
			return "Error"
	
	async def update_metadata(self, token: str, meta_data: dict):
		url = f"{self.base_url}/users/@me/applications/{self.bot.user.id}/role-connection"
		headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
		response = await self.session.put(url, headers=headers, data=json.dumps(meta_data))

		if response.status == 200:
			return "Success"
		else:
			print(await response.json())
			return "Error"
	
	async def refresh(self, token: str, user_id: int):
		url = f"{self.base_url}/oauth2/token"
		headers = {"Content-Type": "application/x-www-form-urlencoded"}
		data = {
			"client_id": self.bot.user.id,
			"client_secret": self.bot.secret,
			"grant_type": "refresh_token",
			"refresh_token": token,
		}
		response = await self.session.post(url, headers=headers, data=data)
		if response.status == 200:
			return response
		else:
			return response
	
	@tasks.loop(hours=6)
	async def refresh_loop(self):
		if self.refresh_task == True:
			return
		self.refresh_task = True
		data = await self.bot.auth.get_all()
		for user in data:
			user_data = await self.refresh(user['refresh_token'], user['_id'])
			if user_data.status != 200:
				continue
			user_data = await user_data.json()
			user['access_token'] = user_data['access_token']
			user['refresh_token'] = user_data['refresh_token']
			user['expires_in'] = user_data['expires_in']
			user['expires_at'] = discord.utils.utcnow() + datetime.timedelta(seconds=user_data['expires_in'])
			await self.bot.auth.upsert(user)
		self.refresh_task = False
	
	@refresh_loop.before_loop
	async def before_refresh(self):
		await self.bot.wait_until_ready()

	def cog_unload(self):
		self.auth_refresh.cancel()

	@app_commands.command(name="link", description="Link your discord account to with OCTANE")
	async def _link(self, interaction: Interaction):
		embed = discord.Embed(description="Press the button below to link your discord account with OCTANE", color=discord.Color.blurple())
		view = discord.ui.View()
		view.add_item(discord.ui.Button(label="Link", style=discord.ButtonStyle.url, url="https://tgk-api.vercel.app/api/linked-role/auth", emoji="🔗"))
		await interaction.response.send_message(embed=embed, view=view)
	
	@app_commands.command(name="update", description="Update your linked roles")
	@app_commands.default_permissions(manage_guild=True)
	@app_commands.describe(user="The user you want to update the roles for", link="The link you want to update", value="The value you want to set the link to")
	@app_commands.choices(link=[app_commands.Choice(name="♡੭𓈒 Beast Donor ♡੭𓈒", value="top_dono"), app_commands.Choice(name="࿔･ﾟ♛ Weekly Topper ♛ ࿔･ﾟ", value="most_active")])
	async def _update(self, interaction: Interaction, user: discord.Member, link: app_commands.Choice[str], value: bool=False):
		data = await self.bot.auth.find(user.id)
		if data is None:
			data = {
				"_id": user.id,
				"access_token": None,
				"refresh_token": None,
				"expires_in": None,
				"expires_at": None,
				"username": user.name,
				"discriminator": user.discriminator,
				"scope": None,
				"metadata": {
					"platform_name": "The Gaming's Kingdom", "platform_username": user.name, "metadata": {}
				}
			}
		
		metadata = await self.get_metadata(data["access_token"])
		if metadata == "Error":
			embed = discord.Embed(description=f"```py\n{await metadata.json()}\n```", color=discord.Color.red())
			return await interaction.response.send_message(embed=embed, ephemeral=True)
		
		if metadata != data['metadata']:
			data['metadata'] = metadata
			await self.bot.auth.upsert(data)
		data['metadata']['metadata'][link.value] = 1 if value == True else 0
		response = await self.update_metadata(data['access_token'], data['metadata'])
		if response == "Error":
			embed = discord.Embed(description=f"Faild Due to some error", color=discord.Color.red())
			return await interaction.response.send_message(embed=embed, ephemeral=True)

		embed = discord.Embed(description=f"Successfully updated {user.mention}'s linked roles {link.name} to {value}", color=discord.Color.green())
		await interaction.response.send_message(embed=embed, ephemeral=False)
		
	@app_commands.command(name="show", description="Show your linked roles")
	@app_commands.describe(user="The user you want to show the linked roles for")
	async def _show(self, interaction: Interaction, user: discord.Member=None):
		user = user if user != None else interaction.user
		data = await self.bot.auth.find(user.id)
		if data is None:
			return await interaction.response.send_message(f"{'you' if user.id == interaction.user.id else user.mention} have not linked your account yet", ephemeral=True)
		
		embed = discord.Embed(title=f"{user.name}'s linked roles", color=discord.Color.blurple(), description="")
		embed.description += f"**Platform Name:** {data['metadata']['platform_name']}\n"
		embed.description += f"**Platform Username:** {data['metadata']['platform_username']}\n"
		for role, value in data['metadata']['metadata'].items():
			embed.description += f"**{role}:** {value}\n"

		await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
	await bot.add_cog(Linked_Roles(bot))