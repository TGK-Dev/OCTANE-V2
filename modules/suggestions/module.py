import discord
from discord import app_commands, Interaction
from discord.ext import commands
from utils.db import Document
from .view import Vote
from typing import Literal
import re


@app_commands.guild_only()
@app_commands.guilds(785839283847954433)
@app_commands.allowed_installs(guilds=True, users=False)
class Suggestion(commands.GroupCog, name="de"):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(Vote())
        self.db = bot.mongo["dank_event"]
        self.bot.locations = Document(self.db, "locations")
        self.bot.phreases = Document(self.db, "phreases")
        self.bot.sugconfig = Document(self.db, "config")
        self.config = self.bot.sugconfig
        self.locations = self.bot.locations
        self.phreases = self.bot.phreases

    suggest = app_commands.Group(
        name="suggest", description="Suggest a feature for the bot"
    )
    admin = app_commands.Group(
        name="admin", description="Admin commands for suggestions"
    )

    @suggest.command(name="location", description="Suggest a location for the bot")
    @app_commands.describe(
        location="location u want to suggest should be related to TGK"
    )
    async def suggest_location(
        self, interaction: Interaction, location: app_commands.Range[str, 1, 50]
    ):
        config = await self.config.find({"_id": interaction.guild_id})
        if not config:
            config = {
                "_id": interaction.guild_id,
                "status": "active",
                "banned_users": [],
            }
            await self.config.insert(config)
        if config["status"] == "inactive":
            return await interaction.response.send_message(
                "Suggestion system is currently shutdown", ephemeral=True
            )
        if interaction.user.id in config["banned_users"]:
            return await interaction.response.send_message(
                "You are banned from using the suggestion system", ephemeral=True
            )

        chl = self.bot.get_channel(1306522156523323403)
        if len(location.lower().split(" ")) > 3:
            return await interaction.response.send_message(
                "Location name should be less than 3 words", ephemeral=True
            )
        embed = discord.Embed(color=self.bot.default_color, description=f"{location}")
        embed.timestamp = discord.utils.utcnow()
        embed.set_author(
            name=interaction.user.name,
            icon_url=interaction.user.avatar.url
            if interaction.user.avatar
            else interaction.user.default_avatar,
        )
        embed.add_field(name="Upvotes", value="```0```", inline=True)
        embed.add_field(name="Downvotes", value="```0```", inline=True)

        embed.set_footer(
            text=f"Location suggestion by {interaction.user.name}",
        )

        msg = await chl.send(embed=embed, view=Vote())
        await interaction.response.send_message(
            "Location suggestion has been sent successfully", ephemeral=True
        )
        data = {
            "_id": msg.id,
            "author": interaction.user.id,
            "location": location,
            "upvotes": 0,
            "downvotes": 0,
            "upvoters": [],
            "downvoters": [],
            "status": "pending",
            "status_reason": None,
            "status_by": None,
        }
        await self.locations.insert(data)

    @suggest.command(name="phrase", description="Suggest a phrease for the bot")
    @app_commands.describe(phrase ="phrease u want to suggest", _type="type of phrease")
    async def suggest_phrease(
        self,
        interaction: Interaction,
        phrase : app_commands.Range[str, 1, 100],
        _type: Literal["win", "lose", "die"],
    ):
        config = await self.config.find({"_id": interaction.guild_id})
        if not config:
            config = {
                "_id": interaction.guild_id,
                "status": "active",
                "banned_users": [],
            }
            await self.config.insert(config)
        if config["status"] == "inactive":
            return await interaction.response.send_message(
                "Suggestion system is currently shutdown", ephemeral=True
            )
        if interaction.user.id in config["banned_users"]:
            return await interaction.response.send_message(
                "You are banned from using the suggestion system", ephemeral=True
            )

        pattern = r"\{x\}"
        if not re.search(pattern, phrase ) and _type == "win":
            return await interaction.response.send_message(
                "Phrease should contain {x} as placeholder", ephemeral=True
            )

        chl = self.bot.get_channel(1306522515966791742)

        embed = discord.Embed(
            color=self.bot.default_color,
            description=f"{phrase }\n\n**Type: {_type.capitalize()}**",
        )
        embed.timestamp = discord.utils.utcnow()
        embed.set_author(
            name=interaction.user.name,
            icon_url=interaction.user.avatar.url
            if interaction.user.avatar
            else interaction.user.default_avatar,
        )
        embed.add_field(name="Upvotes", value="```0```", inline=True)
        embed.add_field(name="Downvotes", value="```0```", inline=True)
        embed.set_footer(
            text=f"Phrase suggestion by {interaction.user.name}",
        )

        msg = await chl.send(embed=embed, view=Vote())
        await interaction.response.send_message(
            "phrase suggestion has been sent successfully", ephemeral=True
        )
        data = {
            "_id": msg.id,
            "author": interaction.user.id,
            "phrease": phrase ,
            "type": _type,
            "upvotes": 0,
            "downvotes": 0,
            "upvoters": [],
            "downvoters": [],
            "status": "pending",
            "status_reason": None,
            "status_by": None,
        }

        await self.phreases.insert(data)

    @admin.command(name="shutdown", description="Shutdown the suggestion system")
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_toggle(self, interaction: Interaction):
        config = await self.config.find({"_id": interaction.guild_id})
        if not config:
            config = {
                "_id": interaction.guild_id,
                "status": "active",
                "banned_users": [],
            }
            await self.config.insert(config)
        if config["status"] == "active":
            config["status"] = "inactive"
            await self.config.update(config)
            await interaction.response.send_message(
                "Suggestion system has been shutdown successfully", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "Suggestion system is already shutdown", ephemeral=True
            )

    @admin.command(
        name="ban", description="Ban a user from using the suggestion system"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_ban(self, interaction: Interaction, user: discord.Member):
        config = await self.config.find({"_id": interaction.guild_id})
        if not config:
            config = {
                "_id": interaction.guild_id,
                "status": "active",
                "banned_users": [],
            }
            await self.config.insert(config)
        if user.id in config["banned_users"]:
            return await interaction.response.send_message(
                "User is already banned from using the suggestion system",
                ephemeral=True,
            )
        config["banned_users"].append(user.id)
        await self.config.update(config)
        await interaction.response.send_message(
            "User has been banned from using the suggestion system", ephemeral=True
        )

    @admin.command(
        name="unban", description="Unban a user from using the suggestion system"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_unban(self, interaction: Interaction, user: discord.Member):
        config = await self.config.find({"_id": interaction.guild_id})
        if not config:
            config = {
                "_id": interaction.guild_id,
                "status": "active",
                "banned_users": [],
            }
            await self.config.insert(config)
        if user.id not in config["banned_users"]:
            return await interaction.response.send_message(
                "User is not banned from using the suggestion system", ephemeral=True
            )
        config["banned_users"].remove(user.id)
        await self.config.update(config)
        await interaction.response.send_message(
            "User has been unbanned from using the suggestion system", ephemeral=True
        )

    @admin.command(name="action", description="Approve a suggestion")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        suggestion="suggestion message id",
        reason="reason for approval",
        action="action to perform",
    )
    async def admin_action(
        self,
        interaction: Interaction,
        action: Literal["rejected", "approved", "closed"],
        suggestion: int,
        reason: str,
    ):
        try:
            msg = await interaction.channel.fetch_message(suggestion)
        except discord.NotFound:
            return await interaction.response.send_message(
                "Message not found", ephemeral=True
            )

        embed = msg.embeds[0]

        if embed.footer.text.lower().startswith("phrase"):
            db = self.phreases
        elif embed.footer.text.lower().startswith("location"):
            db = self.locations
        else:
            return await interaction.response.send_message(
                "Invalid message", ephemeral=True
            )
        data = await db.find({"_id": msg.id})
        if not data:
            return await interaction.response.send_message(
                "Suggestion not found", ephemeral=True
            )

        data["status"] = action
        data["status_reason"] = reason
        data["status_by"] = interaction.user.id

        await db.update(data)

        if len(embed.fields) == 2:
            embed.insert_field_at(
                0,
                name=f"{data['status'].capitalize()} By {interaction.user.name}",
                value=f"{data['status_reason']}",
                inline=False,
            )
        else:
            embed.set_field_at(
                0,
                name=f"{data['status'].capitalize()} By {interaction.user.name}",
                value=f"{data['status_reason']}",
                inline=False,
            )

        if action == "approved":
            embed.color = discord.Color.green()
        elif action == "rejected":
            embed.color = discord.Color.red()
        else:
            embed.color = discord.Color.blue()

        await msg.edit(embed=embed)

        await interaction.response.send_message(
            "Suggestion has been approved successfully", ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Suggestion(bot))
