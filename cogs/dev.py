import datetime
import discord
import io
import contextlib
import textwrap
import re
import aiohttp
import os
import json

from typing import Literal
from traceback import format_exception
from discord import app_commands
from discord.ext import commands, tasks
from typing import List
from utils.views.buttons import Confirm
from utils.checks import is_dev
from utils.converters import clean_code
from utils.paginator import Contex_Paginator, Paginator
from utils.transformer import TimeConverter
from humanfriendly import format_timespan
from utils.db import Document
from utils.views.buttons import Reload


class Dev(commands.Cog, name="dev", description="Dev commands"):
    def __init__(self, bot):
        self.bot = bot
        self.bot.misc = Document(self.bot.db, "misc")
    
    async def cog_auto_complete(self, interaction: discord.Interaction, current:str) -> List[app_commands.Choice[str]]:
        _list =  [
            app_commands.Choice(name=extention, value=extention)
            for extention in self.bot.extensions if current.lower() in extention.lower()
        ]
        return _list[:24]

    dev = app_commands.Group(name="dev", description="Dev commands")
    
    @dev.command(name="reload", description="Reloads a cog")
    @app_commands.autocomplete(cog=cog_auto_complete)
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(is_dev)
    async def reload(self, interaction: discord.Interaction, cog: str):
        await interaction.response.send_message(embed=discord.Embed(description=f"Reloading cog `{cog}`...", color=interaction.client.default_color))
        view = Reload(cog)
        view.children[0].label = f"{cog}"
        try:
            await self.bot.reload_extension(cog)
            await interaction.edit_original_response(embed=discord.Embed(description=f"Successfully reloaded cog `{cog}`", color=interaction.client.default_color), view=view)
        except Exception as e:
            await interaction.edit_original_response(content=None, embed=discord.Embed(description=f"Error while reloading cog `{cog}`: {e}", color=interaction.client.default_color), view=view)
        
        view.message = await interaction.original_response()

    @dev.command(name="sync", description="Syncs a guild/gobal command")
    @app_commands.check(is_dev)
    async def sync(self, interaction: discord.Interaction, guild_id: str=None):
        if guild_id is None:
            await interaction.response.send_message(embed=discord.Embed(description="Syncing global commands...", color=interaction.client.default_color))
            await interaction.client.tree.sync()
            await interaction.edit_original_response(embed=discord.Embed(description="Successfully synced global commands", color=interaction.client.default_color))
        else:
            if guild_id == "*":
                guild = interaction.guild
            else:
                guild = await interaction.client.fetch_guild(int(guild_id))
                if guild is None:
                    return await interaction.response.send_message(embed=discord.Embed(description="Invalid guild id", color=interaction.client.default_color))
            await interaction.response.send_message(embed=discord.Embed(description=f"Syncing guild commands for `{guild.name}`...", color=interaction.client.default_color))
            await interaction.client.tree.sync(guild=guild)
            await interaction.edit_original_response(embed=discord.Embed(description=f"Successfully synced guild commands for `{guild.name}`", color=interaction.client.default_color))
    
    @dev.command(name="servers", description="kill/restart the bot")
    @app_commands.check(is_dev)
    @app_commands.choices(servers=[
        app_commands.Choice(name="NAT", value="e3ea1246"), app_commands.Choice(name="OCT∆NΞ", value="dd089fbe"), app_commands.Choice(name="A.C.E", value="f9a3bf56")
    ])
    async def _host(self, interaction: discord.Interaction, servers: str,signal: Literal["kill", "restart", "start"]):
        view = Confirm(interaction.user, 30)
        await interaction.response.send_message(embed=discord.Embed(description=f"Are you sure you want send {signal} signal to {servers}", color=interaction.client.default_color), view=view)
        view.message = await interaction.original_response()
        await view.wait()

        if view.value:
            await view.interaction.response.edit_message(embed=discord.Embed(description=f"Successfully sent {signal} signal to {servers}", color=interaction.client.default_color), view=None)
            try:
                async with aiohttp.ClientSession() as session:
                    headders = {
                        "Accept": "application/json",
                        "Authorization": f"Bearer {os.environ.get('SPARKED_HOST_TOKEN')}",
                        "Content-Type": "application/json"
                    }
                    data = {
                        "signal": signal
                    }
                    async with session.post(f"https://control.sparkedhost.us/api/client/servers/{servers}/power",
                                            headers=headders, data=json.dumps(data)) as response:
                        await session.close()
            except aiohttp.ContentTypeError:
                pass
        else:
            await interaction.delete_original_response()

    @dev.command(name="get-logs", description="Gets the logs form console")
    @app_commands.check(is_dev)
    async def get_logs(self, interaction: discord.Interaction):
        await interaction.response.send_message(file=discord.File("./discord.log", filename="discord.log"), ephemeral=True, delete_after=120)

    
    @commands.command(name="eval", description="Evaluates a python code")
    async def _eval(self, ctx: commands.Context, *, code):
        if ctx.author.id not in [301657045248114690, 488614633670967307]:
            await ctx.reply(f"{ctx.author.mention} Wow, you're about as qualified to use that command as I am to perform open-heart surgery with a spork. Maybe stick to coloring books instead?", mention_author=True)

        code = clean_code(code)
        local_variables = {
            "discord": discord,
            "commands": commands,
            "bot": self.bot,
            "ctx": ctx,
            "channel": ctx.channel,
            "author": ctx.author,
            "guild": ctx.guild,
            "message": ctx.message
        }

        stdout = io.StringIO()
    
        try:
            with contextlib.redirect_stdout(stdout):

                exec(
                    f"async def func():\n{textwrap.indent(code, '    ')}", local_variables,
                )
                obj = await local_variables["func"]()

                result = f"{stdout.getvalue()}\n-- {obj}\n"
                
        except Exception as e:
            result = "".join(format_exception(e,e,e.__traceback__))
        page = []
        for i in range(0, len(result), 2000):
            page.append(discord.Embed(description=f'```py\n{result[i:i + 2000]}\n```', color=ctx.author.color))
        
        await Contex_Paginator(ctx, page).start(embeded=True, quick_navigation=False)

class Admin(commands.GroupCog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.bot_blacklist = Document(self.bot.db, "blacklist")
        self.bot.bot_blacklist_cache = {}

    blacklist = app_commands.Group(name="blacklist", description="Blacklist commands")
     
    @commands.Cog.listener()
    async def on_ready(self):
        data = await self.bot.bot_blacklist.get_all()
        for i in data:
            self.bot.bot_blacklist_cache[i['_id']] = i

    @blacklist.command(name="add", description="Adds a user to the blacklist")
    @app_commands.describe(user="The user to blacklist", reason="The reason for blacklisting the user")
    @app_commands.checks.has_any_role(785842380565774368, 785845265118265376, 787259553225637889)
    async def add(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        if user.id in [self.bot.user.id, 761834680395497484, 301657045248114690]:
            return await interaction.response.send_message(embed=discord.Embed(description="You can't blacklist me or my developers", color=interaction.client.default_color), ephemeral=True)
        data = await self.bot.bot_blacklist.find(user.id)
        if data: return await interaction.response.send_message(embed=discord.Embed(description=f"{user.mention} is already blacklisted for {data['reason']}", color=interaction.client.default_color), ephemeral=True)

        data = {
            '_id': user.id,
            'reason': reason,
            'banned_by': interaction.user.id,
            'banne_at': datetime.datetime.utcnow()}

        await self.bot.bot_blacklist.insert(data)
        self.bot.bot_blacklist_cache[user.id] = data
        await interaction.response.send_message(embed=discord.Embed(description=f"{user.mention} has been blacklisted for {reason}", color=interaction.client.default_color), ephemeral=False)

        embed = discord.Embed(title="Blacklisted | Added", color=discord.Color.red(), description="")
        embed.description += f"**User:** {user.mention}\n"
        embed.description += f"**ID:** {user.id}\n"
        embed.description += f"**Reason:** {reason}\n"
        embed.description += f"**Banned By:** {interaction.user.mention}\n"
        embed.description += f"**Banned At:** {datetime.datetime.utcnow().strftime('%a, %#d %B %Y, %I:%M %p UTC')}\n"
        embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar)
        embed.set_footer(text=f"ID: {user.id}")
        channel = self.bot.get_channel(1113847572981895310)
        if channel:
            await channel.send(embed=embed)


    @blacklist.command(name="remove", description="Removes a user from the blacklist")
    @app_commands.describe(user="The user to remove from the blacklist", reason="The reason for removing the user from the blacklist")
    @app_commands.checks.has_any_role(785842380565774368, 785845265118265376)
    async def remove(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        data = await self.bot.bot_blacklist.find(user.id)
        if not data: return await interaction.response.send_message(embed=discord.Embed(description=f"{user.mention} is not blacklisted", color=interaction.client.default_color), ephemeral=True)
        await self.bot.bot_blacklist.delete(user.id)
        del self.bot.bot_blacklist_cache[user.id]
        await interaction.response.send_message(embed=discord.Embed(description=f"{user.mention} has been removed from the blacklist", color=interaction.client.default_color), ephemeral=False)
    
        embed = discord.Embed(title="Blacklisted | Removed", color=discord.Color.green(), description="")
        embed.description += f"**User:** {user.mention}\n"
        embed.description += f"**ID:** {user.id}\n"
        embed.description += f"**Reason for Blacklist:** {data['reason']}\n"
        embed.description += f"**Reason for Unblacklist:** {reason}\n"
        embed.description += f"**Unbanned By:** {interaction.user.mention}\n"
        embed.description += f"**Unbanned At:** {datetime.datetime.utcnow().strftime('%a, %#d %B %Y, %I:%M %p UTC')}\n"
        embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar)
        embed.set_footer(text=f"ID: {user.id}")
        channel = self.bot.get_channel(1113847572981895310)
        if channel:
            await channel.send(embed=embed)


    @blacklist.command(name="list", description="Lists all the blacklisted users")
    @app_commands.checks.has_any_role(785842380565774368, 785845265118265376, 787259553225637889)
    async def list(self, interaction: discord.Interaction):
        data = await self.bot.bot_blacklist.get_all()
        if not data: return await interaction.response.send_message(embed=discord.Embed(description="There are no blacklisted users", color=interaction.client.default_color), ephemeral=True)
        page = []
        for i in data:
            user = interaction.guild.get_member(i['_id'])
            if not user: continue
            embed = discord.Embed(color=interaction.client.default_color, description="")
            embed.description += f"**User:** {user.mention}\n"
            embed.description += f"**Reason:** {i['reason']}\n"
            embed.description += f"**Banned By:** {interaction.guild.get_member(i['banned_by']).mention}\n"
            embed.description += f"**Banned At:** {i['banne_at'].strftime('%d/%m/%Y %H:%M:%S')}\n"
            page.append(embed)
        
        await Paginator(interaction, page).start(embeded=True, quick_navigation=False)


    @commands.group(name="admin", description="Admin commands", invoke_without_command=False)
    @commands.has_any_role(785845265118265376, 785842380565774368, 941772431750750218)
    async def admin(self, ctx):
        pass

    @admin.command(name="snipe", description="resets the channels snipes and editsnipes", aliases=['rs', 'rsnipe'])
    @commands.has_any_role(785845265118265376, 785842380565774368, 941772431750750218)
    async def reset_snipe(self, ctx, channel: discord.TextChannel = None):
        if not channel: channel = ctx.channel
        if channel.id not in self.bot.snipes.keys() and channel.id not in self.bot.esnipes.keys(): return await ctx.send(embed=discord.Embed(description=f"There are no snipes in {channel.mention}", color=self.bot.default_color))
        if channel.id in self.bot.snipes.keys(): del self.bot.snipes[channel.id]
        if channel.id in self.bot.esnipes.keys(): del self.bot.esnipes[channel.id]
        await ctx.send(embed=discord.Embed(description=f"Snipes in {channel.mention} have been reset", color=self.bot.default_color))

async def setup(bot):
    await bot.add_cog(Dev(bot), guilds=[discord.Object(999551299286732871), discord.Object(785839283847954433)])
    await bot.add_cog(Admin(bot), guilds=[discord.Object(999551299286732871), discord.Object(785839283847954433)])