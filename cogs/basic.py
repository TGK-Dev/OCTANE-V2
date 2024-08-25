import discord
from discord.ext import commands
from discord import app_commands, Interaction
import asyncio
import datetime
import psutil
import unicodedata
import random
from typing import Literal
from utils.db import Document
from utils.paginator import Paginator
from utils.views.member_view import Member_view


class Basic(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.snipes = {}
        self.bot.esnipes = {}
        self.bot.votes = Document(bot.db, "Votes")

    @app_commands.command(name="stats")
    async def stats(self, interaction: Interaction):
        start = datetime.datetime.now()
        await interaction.response.send_message("Pong!")
        end = datetime.datetime.now()

        embed = discord.Embed(
            title="Bot Stats", description="Bot stats", color=0x00FF00
        )
        embed.add_field(name="Ping", value=f"{(end - start).microseconds / 1000}ms")
        embed.add_field(name="CPU Usage", value=f"{psutil.cpu_percent()}%")
        embed.add_field(
            name="Memory Usage", value=f"{psutil.virtual_memory().percent}%"
        )
        embed.add_field(name="Threads", value=f"{psutil.cpu_count()}")
        embed.add_field(
            name="Uptime",
            value=f"{(datetime.datetime.now() - self.bot.start_time).days} days, {(datetime.datetime.now() - self.bot.start_time).seconds // 3600} hours, {((datetime.datetime.now() - self.bot.start_time).seconds // 60) % 60} minutes, {((datetime.datetime.now() - self.bot.start_time).seconds) % 60} seconds",
        )

        await interaction.edit_original_response(content=None, embed=embed)

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        if before.channel is not None and after.channel is None:
            return
        if member.id != 270904126974590976:
            return
        await asyncio.sleep(2)
        await member.move_to(None)

    @app_commands.command(
        name="snipe", description="Snipe a deleted/edited message from the channel"
    )
    @app_commands.describe(
        type="The type of snipe",
        index="Which # of message do you want to snipe?",
        hidden="Whether the snipe should be hidden or not",
    )
    @app_commands.checks.cooldown(1, 10, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.rename(index="number")
    async def snipe(
        self,
        interaction: Interaction,
        type: Literal["delete", "edit"],
        index: app_commands.Range[int, 1, 10] = None,
        hidden: bool = False,
    ):
        match type:
            case "delete":
                if index is None:
                    try:
                        messages = self.bot.snipes[interaction.channel.id]
                        messages.reverse()
                    except KeyError:
                        embed = discord.Embed(
                            description="There is nothing to snipe!",
                            color=interaction.client.default_color,
                        )
                        return await interaction.response.send_message(
                            embed=embed, ephemeral=True
                        )
                    except Exception:
                        embed = discord.Embed(
                            description="That message doesn't exist!",
                            color=interaction.client.default_color,
                        )
                        return await interaction.response.send_message(
                            embed=embed, ephemeral=True
                        )

                    pages = []
                    for message in messages:
                        author = interaction.guild.get_member(message["author"])
                        if author is None:
                            author = await self.bot.fetch_user(message["author"])
                        embed = discord.Embed(
                            description=message["content"], color=message["color"]
                        )
                        embed.set_author(
                            name=author,
                            icon_url=author.avatar.url
                            if author.avatar
                            else author.default_avatar,
                        )
                        embed.set_footer(
                            text=f"Sniped by {interaction.user}",
                            icon_url=interaction.user.avatar.url
                            if interaction.user.avatar
                            else interaction.user.default_avatar,
                        )
                        if message["attachments"]:
                            embed.set_image(url=message["attachments"])
                        pages.append(embed)

                    return await Paginator(interaction, pages).start(
                        embeded=True, quick_navigation=False, hidden=hidden
                    )
                else:
                    try:
                        message = self.bot.snipes[interaction.channel.id]
                        message.reverse()
                        message = message[index - 1]
                    except KeyError:
                        embed = discord.Embed(
                            description="There is nothing to snipe!",
                            color=interaction.client.default_color,
                        )
                        return await interaction.response.send_message(
                            embed=embed, ephemeral=True
                        )

                    author = interaction.guild.get_member(message["author"])
                    if author is None:
                        author = await self.bot.fetch_user(message["author"])
                    embed = discord.Embed(
                        description=message["content"], color=message["color"]
                    )
                    embed.set_author(
                        name=author,
                        icon_url=author.avatar.url
                        if author.avatar
                        else author.default_avatar,
                    )
                    embed.set_footer(
                        text=f"Sniped by {interaction.user}",
                        icon_url=interaction.user.avatar.url
                        if interaction.user.avatar
                        else interaction.user.default_avatar,
                    )
                    if message["attachments"]:
                        embed.set_image(url=message["attachments"])
                    embed.timestamp = datetime.datetime.now()

                    return await interaction.response.send_message(
                        embed=embed, ephemeral=hidden
                    )

            case "edit":
                if not index:
                    try:
                        message = self.bot.esnipes[interaction.channel.id]
                        message.reverse()
                        message = message[index - 1]
                    except Exception:
                        embed = discord.Embed(
                            description="That message doesn't exist!",
                            color=interaction.client.default_color,
                        )
                        return await interaction.response.send_message(
                            embed=embed, ephemeral=True
                        )

                    for message in messages:
                        author = interaction.guild.get_member(message["author"])
                        embed = discord.Embed(
                            description=f"**Before:**\n{message['before']}\n\n**After:**\n{message['after']}",
                            color=author.color
                            if author is not None
                            else self.bot.default_color,
                        )
                        embed.set_author(
                            name=author,
                            icon_url=author.avatar.url
                            if author.avatar
                            else author.default_avatar,
                        )
                        embed.set_footer(
                            text=f"Sniped by {interaction.user}",
                            icon_url=interaction.user.avatar.url
                            if interaction.user.avatar
                            else interaction.user.default_avatar,
                        )

                        pages.append(embed)
                        return await Paginator(interaction, pages).start(
                            embeded=True, quick_navigation=False, hidden=hidden
                        )
                else:
                    try:
                        message = self.bot.esnipes[interaction.channel.id]
                        message.reverse()
                        message = message[index - 1]
                    except Exception:
                        embed = discord.Embed(
                            description="That message doesn't exist!",
                            color=interaction.client.default_color,
                        )
                        return await interaction.response.send_message(
                            embed=embed, ephemeral=True
                        )

                    author = interaction.guild.get_member(message["author"])
                    embed = discord.Embed(
                        description=f"**Before:**\n{message['before']}\n\n**After:**\n{message['after']}",
                        color=author.color
                        if author is not None
                        else self.bot.default_color,
                    )
                    embed.set_author(
                        name=author,
                        icon_url=author.avatar.url
                        if author.avatar
                        else author.default_avatar,
                    )
                    embed.set_footer(
                        text=f"Sniped by {interaction.user}",
                        icon_url=interaction.user.avatar.url
                        if interaction.user.avatar
                        else interaction.user.default_avatar,
                    )

                    return await interaction.response.send_message(
                        embed=embed, ephemeral=hidden
                    )

    @app_commands.user_install()
    @app_commands.command(
        name="enter", description="Tell everyone that you enter the chat"
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def enter(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"**{interaction.user}** has entered the room! <:pepeEnter:1274302538472095835>"
        )

    @app_commands.command(
        name="exit", description="Tell everyone that you leave the chat"
    )
    @app_commands.user_install()
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.checks.cooldown(1, 10, key=lambda i: (i.guild_id, i.user.id))
    async def leave(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"**{interaction.user}** has left the room! <:pepeExit:1274302544113565812>"
        )

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot or message.guild is None or message.content is None:
            return

        if message.channel.id not in self.bot.snipes.keys():
            self.bot.snipes[message.channel.id] = []

        if len(self.bot.snipes[message.channel.id]) == 10:
            self.bot.snipes[message.channel.id].pop(0)
        data = {
            "author": message.author.id,
            "content": message.content,
            "attachments": [],
            "color": message.author.color,
        }
        if len(message.attachments) > 0:
            if message.attachments[0].url.endswith(
                (".png", ".jpg", ".jpeg", ".gif", ".webp")
            ):
                data["attachments"] = message.attachments[0].url
        self.bot.snipes[message.channel.id].append(data)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot or before.guild is None or before.content is None:
            return

        if before.channel.id not in self.bot.esnipes.keys():
            self.bot.esnipes[before.channel.id] = []

        if len(self.bot.esnipes[before.channel.id]) == 10:
            self.bot.esnipes[before.channel.id].pop(0)

        self.bot.esnipes[before.channel.id].append(
            {
                "author": before.author.id,
                "before": before.content,
                "after": after.content,
                "color": before.author.color,
            }
        )

    @app_commands.command(name="whois", description="Get information about a user")
    @app_commands.describe(member="The user to get information about")
    async def whois(self, interaction: Interaction, member: discord.Member = None):
        member = member if member else interaction.user

        embed = discord.Embed(title=f"User Info - {member.global_name}")
        embed.set_thumbnail(
            url=member.avatar.url if member.avatar else member.default_avatar.url
        )

        embed.add_field(name="<:authorized:991735095587254364> ID:", value=member.id)
        embed.add_field(
            name="<:displayname:991733326857654312> Display Name:",
            value=member.display_name,
        )

        embed.add_field(name="<:bot:991733628935610388> Bot Account:", value=member.bot)

        embed.add_field(
            name="<:settings:991733871118917683> Account creation:",
            value=member.created_at.strftime("%d/%m/%Y %H:%M:%S"),
        )
        embed.add_field(
            name="<:join:991733999477203054> Server join:",
            value=member.joined_at.strftime("%d/%m/%Y %H:%M:%S"),
        )

        if not member.bot:
            view = Member_view(self.bot, member, interaction)
            await interaction.response.send_message(embed=embed, view=view)
            view.message = await interaction.original_response()
        else:
            await interaction.response.send_message(embed=embed)

    @commands.command(name="cook", description="cook new emoji", aliases=["c"])
    async def _cook(
        self, ctx: commands.Context, frist: str, second: str, third: str = None
    ):
        if (
            not ctx.author.guild_permissions.administrator
            and ctx.channel.id != 785849567518130176
        ):
            return await ctx.reply(
                "You can't use this command here use it in <#785849567518130176>",
                delete_after=20,
            )

        def to_string(c):
            digit = f"{ord(c):x}"
            unicodedata.name(c, "Name not found.")
            c = "\\`" if c == "`" else c
            return f"{digit}"

        domains = [
            "emk.vercel.app",
            "emjk.vercel.app",
            "emojk.vercel.app",
            "emojik.vercel.app",
            "emoji-kitchen.vercel.app",
        ]
        url = f"https://{random.choice(domains)}/s/{to_string(frist)}_{to_string(second)}?size=200"

        embed = discord.Embed(color=self.bot.default_color)
        embed.set_image(url=url)
        await ctx.send(embed=embed)


class Appeal_server(commands.GroupCog, name="appeal"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="reason", description="Get the reason for your ban")
    @app_commands.describe(member="The member to get the reason for")
    @app_commands.checks.has_permissions(ban_members=True)
    async def reason(self, interaction: Interaction, member: discord.Member):
        main_server = self.bot.get_guild(785839283847954433)
        try:
            ban = await main_server.fetch_ban(member)
        except discord.NotFound:
            return await interaction.response.send_message(
                f"{member.mention} is not banned", ephemeral=True
            )

        await interaction.response.send_message(
            f"The reason for {member.mention}'s ban is: {ban.reason if ban.reason else 'No reason provided'}",
            ephemeral=False,
        )

    @app_commands.command(name="aproove", description="Aproove an appeal")
    @app_commands.describe(
        member="The member to aproove", reason="The reason for aprooving the appeal"
    )
    @app_commands.checks.has_permissions(ban_members=True)
    async def aproove(
        self, interaction: Interaction, member: discord.Member, reason: str
    ):
        main_server = self.bot.get_guild(785839283847954433)
        try:
            await main_server.fetch_ban(member)
        except discord.NotFound:
            return await interaction.response.send_message(
                f"{member.mention} is not banned", ephemeral=True
            )

        await main_server.unban(member, reason=reason)

        await interaction.response.send_message(
            f"{member.mention} You have been unbanned from {main_server.name} for the reason: {reason}\nYou can now rejoin the server at https://discord.gg/tgk",
            ephemeral=False,
        )


class Ban_battle(commands.GroupCog, name="banbattle"):
    def __init__(self, bot):
        self.bot = bot
        self.battle_guild: discord.Guild = None
        self.battle_data = {}

    staff = app_commands.Group(
        name="staff", description="Staff commands for the ban battle"
    )

    @commands.Cog.listener()
    async def on_ready(self):
        self.battle_guild = await self.bot.fetch_guild(1118244586008084581)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.guild.id != self.battle_guild.id:
            return
        if member.bot:
            await member.kick(reason="Bots are not allowed in the ban battle")
        if member.id == self.battle_data["host"]:
            role = self.battle_guild.get_role(1118486572115959820)
            await member.add_roles(role)

    @staff.command(name="setup", description="Setup the ban battle")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup(self, interaction: Interaction):
        if interaction.guild.id == self.battle_guild.id:
            return await interaction.response.send_message(
                "You can't setup the ban battle in the ban battle server",
                ephemeral=True,
            )
        await interaction.response.send_message(
            embed=discord.Embed(
                description="<a:loading:1004658436778229791> Setting up the ban battle..."
            ),
            ephemeral=True,
        )
        over_write = {
            self.battle_guild.default_role: discord.PermissionOverwrite(
                send_messages=False
            ),
            self.battle_guild.get_role(
                1118486572115959820
            ): discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        battle_channel = await self.battle_guild.create_text_channel(
            name="Battle-ground",
            topic="The battle ground for the ban battle",
            category=self.battle_guild.get_channel(1118244586008084584),
            overwrites=over_write,
        )
        inv = battle_channel.create_invite(max_usse=100)
        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(label="Join", style=discord.ButtonStyle.url, url=inv.url)
        )
        self.battle_data["channel"] = battle_channel
        self.battle_data["inv"] = inv.url
        self.battle_data["host"] = interaction.user.id
        await interaction.edit_original_response(
            embed=discord.Embed(
                description="Successfully setup the ban battle tap button below to join"
            ),
            ephemeral=True,
            view=view,
        )

    @staff.command(name="clean-up", description="Clean up the ban battle")
    @app_commands.checks.has_permissions(administrator=True)
    async def clean_up(self, interaction: Interaction):
        await interaction.response.send_message(
            embed=discord.Embed(
                description="<a:loading:1004658436778229791> Cleaning up the ban battle..."
            ),
            ephemeral=True,
        )
        async for ban in self.battle_guild.bans(limit=None):
            if ban.user.reason != "Eliminated from the ban battle":
                continue
            await self.battle_guild.unban(ban.user, reason="Ban battle clean up")
            await asyncio.sleep(1)
        for member in self.battle_guild.members:
            if member.id == self.battle_data["host"]:
                continue
            await member.kick(reason="Ban battle clean up")
            await asyncio.sleep(1)
        for invites in await self.battle_guild.invites():
            await invites.delete(reason="Ban battle clean up")
            await asyncio.sleep(1)
        await interaction.edit_original_response(
            embed=discord.Embed(
                description="Successfully cleaned up the ban battle\nYou will be kick from the server after 10 seconds"
            ),
            ephemeral=True,
        )
        await asyncio.sleep(10)
        await interaction.user.kick(reason="Ban battle clean up")
        await self.battle_data["channel"].delete()
        self.battle_data = {}

    @staff.command(name="add", description="Add a user to the ban battle event manager")
    @app_commands.checks.has_permissions(administrator=True)
    async def add(self, interaction: Interaction, member: discord.Member):
        if interaction.guild.id != self.battle_guild.id:
            return await interaction.response.send_message(
                "You can only use this command in the ban battle server", ephemeral=True
            )
        role = interaction.guild.get_role(1118486572115959820)
        await member.add_roles(role)
        await interaction.response.send_message(
            f"Successfully added {member.mention} to the ban battle event manager",
            ephemeral=True,
        )


class Logging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.webhook = None

    @commands.Cog.listener()
    async def on_ready(self):
        self.webhook = await self.bot.fetch_webhook(1122516717562761226)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.guild is None:
            return
        if message.guild.id != 785839283847954433:
            return

        embeds = []
        embed = discord.Embed(
            title="Message | Deleted", description="", color=message.author.color
        )
        embed.description += f"\n**Channel:** `{message.channel.name} | {message.channel.id}` {message.channel.mention}"
        embed.description += f"\n**Author:** {message.author.mention}"
        embed.description += (
            "\n**Message:**" + message.content
            if message.content is not None
            else "`None`"
        )
        embed.description += (
            f"\n**Created At:** {message.created_at.strftime('%d/%m/%Y %H:%M:%S')}"
        )
        if message.reference is not None:
            try:
                ref_message = await message.channel.fetch_message(
                    message.reference.message_id
                )
                embed.description += f"\n**Replying to:** {ref_message.author.mention}"
                embed.description += (
                    f"\n**Reply Message Content:** {ref_message.content}"
                )
            except discord.NotFound:
                pass
        embed.description += f"\n**Jump:** [Click Here]({message.jump_url})"
        if len(message.attachments) > 0:
            files = []
            for file in message.attachments:
                files.append(f"[{file.filename}]({file.url})")
            embed.description += f"\n**Attachments:** {', '.join(files)}\n"
        embed.set_author(
            name=message.author,
            icon_url=message.author.avatar.url
            if message.author.avatar
            else message.author.default_avatar,
        )
        embed.set_footer(
            text=f"Author ID: {message.author.id} | Message ID: {message.id}"
        )
        embed.timestamp = datetime.datetime.utcnow()

        embeds.append(embed)
        if len(message.embeds) > 0:
            for embed in message.embeds:
                embeds.append(embed)
        try:
            await self.webhook.send(embeds=embeds)
        except AttributeError:
            self.webhook = await self.bot.fetch_webhook(1122516717562761226)
            await self.webhook.send(embeds=embeds)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.guild is None:
            return
        if before.guild.id != 785839283847954433:
            return
        if before.content == after.content:
            return

        embeds = []
        embed = discord.Embed(
            title="Message | Edited", description="", color=after.author.color
        )
        embed.description += f"\n**Channel:** `{before.channel.name} | {before.channel.id}` {before.channel.mention}"
        embed.description += f"\n**Author:** {before.author.mention}"
        embed.description += (
            "\n**Before:**" + before.content if before.content is not None else "`None`"
        )
        embed.description += (
            f"\n**After:** {after.content if after.content is not None else '`None`'}"
        )
        embed.description += (
            f"\n**Created At:** {before.created_at.strftime('%d/%m/%Y %H:%M:%S')}"
        )
        embed.description += f"\n**Jump:** {before.jump_url}"
        if len(before.attachments) > 0:
            files = []
            for file in before.attachments:
                files.append(f"[{file.filename}]({file.url})")
            embed.description += f"\n**Attachments:** {', '.join(files)}"
        embed.set_author(
            name=before.author,
            icon_url=before.author.avatar.url
            if before.author.avatar
            else before.author.default_avatar,
        )
        embed.set_footer(
            text=f"Author ID: {before.author.id} | Message ID: {before.id}"
        )
        embed.timestamp = datetime.datetime.utcnow()

        if before.author.bot:
            if before._interaction:
                embed.description += f"\n**Command:** {before._interaction.name}"
                embed.description += (
                    f"\n**Command User:** {before._interaction.user.mention}"
                )

        embeds.append(embed)
        if len(before.embeds) > 0:
            for embed in before.embeds:
                embed = discord.Embed.from_dict(embed.to_dict())
                if embed.title:
                    embed.title += "| Before Edit"
                else:
                    embed.title = "| Before Edit"
                embeds.append(embed)
        if len(after.embeds) > 0:
            for embed in after.embeds:
                embed = discord.Embed.from_dict(embed.to_dict())
                if embed.title:
                    embed.title += "| After Edit"
                else:
                    embed.title = "| After Edit"
                embeds.append(embed)

        try:
            await self.webhook.send(embeds=embeds)
        except AttributeError:
            self.webhook = await self.bot.fetch_webhook(1122516717562761226)
            await self.webhook.send(embeds=embeds)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        if not payload.guild_id:
            return
        if not payload.channel_id:
            return
        if payload.channel_id != 1103892836564357180:
            return
        data = payload.data
        try:
            msg = discord.Message(
                state=self.bot._connection,
                channel=self.bot.get_channel(payload.channel_id),
                data=data,
            )
        except KeyError:
            return
        embed = msg.embeds[0]
        if "**Ready to be watered!**" in embed.description:
            gc = self.bot.get_channel(785847439579676672)
            await gc.send(
                f"Hey fellow tree lovers! Our server tree is ready to be watered! Come and water it at {msg.jump_url}",
                delete_after=30,
            )


class karuta(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="karuta-access", aliases=["ka"])
    async def karuta_access(self, ctx):
        if not ctx.guild:
            return
        if ctx.author.guild.id != 785839283847954433:
            return
        blacklist_role = ctx.guild.get_role(1121782006628503683)
        access_role = ctx.guild.get_role(1034072149247397938)
        if blacklist_role in ctx.author.roles:
            await ctx.author.remove_roles(access_role)
            return await ctx.send("You are blacklisted from using this command!")
        if access_role in ctx.author.roles:
            await ctx.author.remove_roles(access_role)
            return await ctx.send("Your access to the karuta has been revoked!")
        await ctx.author.add_roles(access_role)
        return await ctx.send("You now have access to the karuta commands!")

    @commands.command(name="karuta-remove", aliases=["kr"])
    async def karuta_remove(self, ctx, user: discord.Member):
        if not ctx.guild:
            return
        if ctx.author.guild.id != 785839283847954433:
            return
        access_role = ctx.guild.get_role(1034072149247397938)
        if ctx.author.id not in [
            538061886386733067,
            488614633670967307,
            677443545656721409,
        ]:
            return await ctx.send("You can't use this command!")
        await user.remove_roles(access_role)
        await ctx.send("User has been removed from the karuta access list")

    @commands.command(name="karuta-bl")
    @commands.has_permissions(ban_members=True)
    async def karuta_bl(self, ctx, user: discord.Member):
        if not ctx.guild:
            return
        if ctx.author.guild.id != 785839283847954433:
            return
        blacklist_role = ctx.guild.get_role(1121782006628503683)
        access_role = ctx.guild.get_role(1034072149247397938)
        if blacklist_role in user.roles:
            await user.remove_roles(access_role)
            await user.add_roles(blacklist_role)
            await ctx.send("User is already blacklisted")
        else:
            await user.add_roles(blacklist_role)
            await user.remove_roles(access_role)
            await ctx.send("User has been blacklisted")


async def setup(bot):
    await bot.add_cog(Basic(bot))
    await bot.add_cog(Appeal_server(bot), guilds=[discord.Object(988761284956799038)])
    await bot.add_cog(karuta(bot))
    await bot.add_cog(Logging(bot))
