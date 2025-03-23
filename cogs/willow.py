import datetime
import discord
from discord.ext import commands
from discord import app_commands
from utils.db import Document
from utils.paginator import Paginator
from utils.converters import chunk
from utils.views.modal import General_Modal
from utils.views.buttons import Confirm
from typing import List, TypedDict


class UserBumps(TypedDict):
    user_id: int
    bumps: int
    last_bump: datetime.datetime


class Guild(TypedDict):
    guild_id: int
    thanks_message: str
    available_message: str
    ping_role: int


class willow(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.message_db = Document(self.bot.db, "willow_bump_config")
        self.bump_db = Document(self.bot.db, "willow_bump")

    bumps = app_commands.Group(
        name="bumps", description="Willow Bump commands", guild_only=True
    )

    bump = app_commands.Group(
        name="bump",
        description="bump admin commands",
        guild_only=True,
    )

    config = app_commands.Group(
        name="config",
        description="Willow Bump configuration",
        guild_only=True,
        parent=bump,
    )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild:
            return
        if (
            message.guild.id == 1334016396228689961
            and message.channel.id == 1334016397491044415
            and message.author.id == 813077581749288990
        ):
            if len(message.embeds) == 0:
                return

            embed: discord.Embed = message.embeds[0]
            config = await self.message_db.find({"guild_id": message.guild.id})

            if not config:
                return

            if embed.description.startswith("Your server can be"):
                embed = discord.Embed(
                    description=config["available_message"],
                    color=discord.Color.green(),
                )
                role = message.guild.get_role(config["ping_role"])
                if role:
                    await message.reply(
                        content=f"{role.mention} bump is now available </bump:959230305699500072>",
                        embed=embed,
                    )
                else:
                    await message.reply(
                        content="Bump is now available </bump:959230305699500072>",
                        embed=embed,
                    )

                return
            if (
                embed.description.startswith("**Thanks for bumping")
                and message._interaction.name == "bump"
            ):
                user = message._interaction.user
                user_data = await self.bump_db.find({"user_id": user.id})
                if not user_data:
                    user_data = {
                        "user_id": user.id,
                        "bumps": 1,
                        "last_bump": discord.utils.utcnow(),
                    }
                    await self.bump_db.insert(user_data)
                else:
                    user_data["bumps"] += 1
                    user_data["last_bump"] = discord.utils.utcnow()

                    await self.bump_db.update(user_data)
                await message.reply(
                    f"{user.mention}",
                    embed=discord.Embed(
                        description=config["thanks_message"],
                        color=discord.Color.green(),
                    ),
                )

    @bumps.command(name="stats", description="Get your bump stats")
    @app_commands.describe(user="User to get stats for")
    async def _stats(
        self, interaction: discord.Interaction, user: discord.Member = None
    ):
        if user is None:
            user = interaction.user
        user: discord.Member
        user_data = await self.bump_db.find({"user_id": user.id})
        if not user_data:
            return await interaction.response.send_message(
                f"{user.mention} You have not bumped yet", ephemeral=True
            )
        embed = discord.Embed(
            description=f"<:W_pinkarrow:1339811750949683294> Bumps: {user_data['bumps']}",
            color=discord.Color.green(),
        )
        embed.set_author(
            name=f"{user.name}'s Bump Stats",
            icon_url=user.display_avatar.url if user.avatar else user.default_avatar,
        )
        embed.set_footer(text="Last bump")
        embed.timestamp = user_data["last_bump"]
        await interaction.response.send_message(embed=embed)

    @bumps.command(name="leaderboard", description="Get the bump leaderboard")
    async def _leaderboard(self, interaction: discord.Interaction):
        users: List[UserBumps] = await self.bump_db.get_all()
        users = sorted(users, key=lambda x: x["bumps"], reverse=True)
        chunked = chunk(users, 10)
        pages = []
        emoji = "<:W_pinkarrow:1339811750949683294> "
        for cunked in chunked:
            embed = discord.Embed(
                description="",
                color=discord.Color.green(),
            )
            embed.set_author(
                name=f"{interaction.guild.name} Bump Leaderboard",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
            )
            for i, user in enumerate(cunked):
                member = interaction.guild.get_member(user["user_id"])
                if not member:
                    try:
                        member = await interaction.client.fetch_user(user["user_id"])
                    except discord.HTTPException:
                        continue

                if member.id == interaction.user.id:
                    embed.description += "📌 "

                if users.index(user) == 0:
                    embed.description += f"🥇 **{member.name}** {emoji} {user['bumps']}"
                elif users.index(user) == 1:
                    embed.description += f"🥈 **{member.name}** {emoji} {user['bumps']}"
                elif users.index(user) == 2:
                    embed.description += f"🥉 **{member.name}** {emoji} {user['bumps']}"
                else:
                    embed.description += f"{users.index(user) + 1}. **{member.name}** {emoji} {user['bumps']}"
                embed.description += "\n"

            pages.append(embed)
        if len(pages) == 0:
            return await interaction.response.send_message(
                "Leaderboard is empty", ephemeral=True
            )
        if len(pages) == 1:
            return await interaction.response.send_message(embed=pages[0])
        paginator = Paginator(
            pages=pages,
            interaction=interaction,
        )
        await paginator.start(
            quick_navigation=False, embeded=True, hidden=False, timeout=20
        )

    @bump.command(name="set", description="Set user bump count")
    @app_commands.describe(user="User to set bump count for", bumps="Bump count")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def _set(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        bumps: int = 0,
    ):
        user_data = await self.bump_db.find({"user_id": user.id})
        if not user_data:
            return await interaction.response.send_message(
                f"{user.mention} has not bumped yet", ephemeral=True
            )
        user_data["bumps"] = bumps
        await self.bump_db.update(user_data)
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"Set {user.mention}'s bump count to {bumps}",
                color=discord.Color.green(),
            ),
        )

    @config.command(name="message", description="Configure the bump channel")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.choices(
        option=[
            app_commands.Choice(name="Bump Available", value="available_message"),
            app_commands.Choice(name="Bump Thanks", value="thanks_message"),
        ]
    )
    async def _config(
        self, interaction: discord.Interaction, option: str, edit: bool = False
    ):
        config = await self.message_db.find({"guild_id": interaction.guild.id})
        if not config:
            config = {
                "guild_id": interaction.guild.id,
                "thanks_message": "",
                "available_message": "",
            }
            await self.message_db.insert(config)
        if edit:
            modal = General_Modal(
                title=f"Editing {option} message", interaction=interaction
            )
            message = discord.ui.TextInput(
                label="Message",
                style=discord.TextStyle.long,
                max_length=2000,
                placeholder="Message",
                default=config[option] if config[option] else None,
            )
            modal.add_item(message)
            await interaction.response.send_modal(modal)

            await modal.wait()
            if modal.value is not True:
                return
            embed = discord.Embed(
                description=f"{message.value}\n",
                color=discord.Color.green(),
            )
            confirm = Confirm(
                timeout=30,
                user=interaction.user,
            )
            await modal.interaction.response.send_message(
                content=f"Are you sure you want to set the {'`Bump Available`' if option == 'available_message' else '`Bump Thanks`'} message with below embed?",
                embed=embed,
                view=confirm,
            )
            confirm.message = await modal.interaction.original_response()
            await confirm.wait()

            if confirm.value is False:
                return await confirm.interaction.response.edit_message(
                    content="Cancelled", embed=None, view=None
                )
            if confirm.value is True:
                config[option] = message.value
                print(message.value)
                await self.message_db.update(config)
                await confirm.interaction.response.edit_message(
                    content="Successfully updated the message", view=None
                )
            return

        if option == "available_message":
            embed = discord.Embed(
                description=config["available_message"],
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        if option == "thanks_message":
            embed = discord.Embed(
                description=config["thanks_message"],
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

    @config.command(name="ping", description="Configure the ping role")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def _ping(self, interaction: discord.Interaction, role: discord.Role = None):
        config = await self.message_db.find({"guild_id": interaction.guild.id})
        if not config:
            config = {
                "guild_id": interaction.guild.id,
                "thanks_message": "",
                "available_message": "",
                "ping_role": None,
            }
            await self.message_db.insert(config)
        if role is None:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"Current ping role is {(interaction.guild.get_role(config['ping_role'])).mention if config['ping_role'] else 'None'}",
                    color=discord.Color.green(),
                ),
            )

        config["ping_role"] = role.id
        await self.message_db.update(config)
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"Successfully set the ping role to {role.mention}",
                color=discord.Color.green(),
            ),
        )

    @config.command(name="view", description="View the bump config")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def _view(self, interaction: discord.Interaction):
        config = await self.message_db.find({"guild_id": interaction.guild.id})
        if not config:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description="No config found",
                    color=discord.Color.red(),
                ),
            )
        available_message = config["available_message"]
        thanks_message = config["thanks_message"]

        available_embed = discord.Embed(
            description=available_message if available_message else "None",
            color=discord.Color.green(),
        )
        available_embed.set_author(
            name="Bump Available Message",
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
        )

        thanks_embed = discord.Embed(
            description=thanks_message if thanks_message else "None",
            color=discord.Color.green(),
        )
        thanks_embed.set_author(
            name="Bump Thanks Message",
        )

        ping_role = config["ping_role"]
        ping_embed = discord.Embed(
            description=f"Ping Role: {(interaction.guild.get_role(ping_role)).mention if ping_role else 'None'}",
            color=discord.Color.green(),
        )

        ping_embed.set_author(
            name="Ping Role",
        )

        await interaction.response.send_message(
            embeds=[available_embed, thanks_embed, ping_embed], ephemeral=False
        )


async def setup(bot):
    await bot.add_cog(willow(bot), guilds=[discord.Object(id=1334016396228689961)])
