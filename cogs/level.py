import asyncio
from io import BytesIO
import discord
import math
import datetime
from discord import app_commands
from discord import Interaction
from discord.ext import commands
from utils.db import Document
from utils.paginator import Paginator
from PIL import Image, ImageDraw, ImageFont, ImageChops
from utils.converters import chunk


class Level_DB:
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.mongo["Levels"]
        self.ranks = Document(self.db, "Ranks")
        self.config = Document(self.db, "RankConfig")
        self.config_cache = {}
        self.level_cache = {}

    async def get_config(self, guild: discord.Guild):
        if guild.id in self.config_cache.keys():
            return self.config_cache[guild.id]
        config = await self.config.find(guild.id)
        if config is None:
            config = await self.guild_config_template(guild)
        self.config_cache[guild.id] = config
        return config

    async def update_config(self, guild: discord.Guild, data: dict):
        await self.config.update(data)
        self.config_cache[guild.id] = data

    async def count_level(self, expirience: int):
        if expirience < 35:
            return 0
        level: int = math.floor(math.sqrt((expirience - 35) / 20)) + 1
        return level

    async def count_xp(self, level: int):
        if level < 1:
            return 0
        experience = 20 * (level - 1) ** 2 + 35
        return experience

    async def level_template(self, member: discord.Member):
        data = {
            "_id": member.id,
            "xp": 1,
            "level": 0,
            "weekly": 0,
            "last_updated": None,
            "messages": {},
        }
        await self.ranks.insert(data)
        return data

    async def guild_config_template(self, guild: discord.Guild):
        data = {
            "_id": guild.id,
            "enabled": False,
            "cooldown": 8,
            "announcement_channel": None,
            "clear_on_leave": True,
            "blacklist": {
                "channels": [],
                "roles": [],
            },
            "global_multiplier": 1,
            "multipliers": {
                "roles": {},
                "channels": {},
            },
            "rewards": {},
            "weekly": {
                "required_messages": None,
                "role": None,
            },
        }
        await self.config.insert(data)
        return data

    async def get_member_level(self, member: discord.Member):
        if member.id in self.level_cache.keys():
            return self.level_cache[member.id]
        data = await self.ranks.find(member.id)
        if data is None:
            data = await self.level_template(member)
        self.level_cache[member.id] = data
        return data

    async def update_member_level(self, member: discord.Member, data: dict):
        self.level_cache[member.id] = data
        try:
            await self.ranks.update(data)
        except Exception:
            pass

    async def millify(self, n):
        n = float(n)
        millnames = ["", " K", " M", " Bil"]
        millidx = max(
            0,
            min(
                len(millnames) - 1,
                int(math.floor(0 if n == 0 else math.log10(abs(n)) / 3)),
            ),
        )

        return f"{round(n / 10**(3 * millidx),1):0}{millnames[millidx]}"

    async def round_pfp(self, pfp: discord.Member | discord.Guild):
        if isinstance(pfp, discord.Member):
            if pfp.avatar is None:
                pfp = pfp.default_avatar.with_format("png")
            else:
                pfp = pfp.avatar.with_format("png")
        else:
            pfp = pfp.icon.with_format("png")

        pfp = BytesIO(await pfp.read())
        pfp = Image.open(pfp)
        pfp = pfp.resize((124, 124), Image.Resampling.LANCZOS).convert("RGBA")

        bigzise = (pfp.size[0] * 3, pfp.size[1] * 3)
        mask = Image.new("L", bigzise, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + bigzise, fill=255)
        mask = mask.resize(pfp.size, Image.Resampling.LANCZOS)
        mask = ImageChops.darker(mask, pfp.split()[-1])
        pfp.putalpha(mask)

        return pfp

    async def create_rank_card(
        self, member: discord.Member, rank: str, level: str, exp: str, weekly: str
    ):
        base_image = Image.open("./assets/rank_card.png")
        profile = member.avatar.with_format("png")
        profile = await self.round_pfp(member)
        profile = profile.resize((124, 124), Image.Resampling.LANCZOS).convert("RGBA")

        user: discord.User = await self.bot.fetch_user(member.id)
        if user.banner is None:
            try:
                banner = Image.new("RGBA", (372, 131), user.accent_color.to_rgb())
            except AttributeError:
                banner = Image.new("RGBA", (372, 131), (0, 0, 0, 255))
            base_image.paste(banner, (0, 0), banner)
        else:
            banner = user.banner.with_format("png")
            banner = BytesIO(await banner.read())
            banner = Image.open(banner)
            banner = banner.resize((372, 131), Image.Resampling.LANCZOS).convert("RGBA")
            base_image.paste(banner, (0, 0), banner)

        pfp_backdrop = Image.new("RGBA", (140, 140), (0, 0, 0, 0))
        back_draw = ImageDraw.Draw(pfp_backdrop)
        back_draw.ellipse((3, 3, 137, 137), fill=(33, 33, 33, 255))
        base_image.paste(pfp_backdrop, (16, 33), pfp_backdrop)

        base_image.paste(profile, (25, 41), profile)

        draw = ImageDraw.Draw(base_image)
        draw.text(
            (115, 180),
            member.display_name,
            fill="#FFFFFF",
            font=ImageFont.truetype("./assets/fonts/Symbola.ttf", 30),
        )

        draw.text(
            (28, 277),
            f"{str(rank)}",
            fill="#6659CE",
            font=ImageFont.truetype("./assets/fonts/DejaVuSans.ttf", 35),
        )
        draw.text(
            (206, 277),
            f"{str(level)}",
            fill="#6659CE",
            font=ImageFont.truetype("./assets/fonts/DejaVuSans.ttf", 35),
        )
        draw.text(
            (28, 389),
            f"{str(exp)}",
            fill="#6659CE",
            font=ImageFont.truetype("./assets/fonts/DejaVuSans.ttf", 35),
        )
        draw.text(
            (206, 389),
            f"{str(weekly)}",
            fill="#6659CE",
            font=ImageFont.truetype("./assets/fonts/DejaVuSans.ttf", 35),
        )
        return base_image


class Level(commands.GroupCog):
    def __init__(self, bot):
        self.bot = bot
        self.levels = Level_DB(bot)
        self.bot.level = self.levels
        self.webhook = None

    weekly = app_commands.Group(name="weekly", description="Weekly commands")

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in await self.levels.config.get_all():
            self.levels.config_cache[guild["_id"]] = guild

        for member in await self.levels.ranks.get_all():
            self.levels.level_cache[member["_id"]] = member

        channel = self.bot.get_channel(999736058071744583)
        for webhook in await channel.webhooks():
            if webhook.user.id == self.bot.user.id:
                self.webhook = webhook
                break
        if self.webhook is None:
            avatar = await self.bot.user.avatar.read()
            self.webhook = await channel.create_webhook(
                name="Banish Logs", avatar=avatar
            )

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            if message._interaction:
                self.bot.dispatch("slash_command", message)
            return
        if message.guild is None:
            return

        data = await self.levels.get_member_level(message.author)

        if data["last_updated"] is None:
            self.bot.dispatch("level_up", message, data)
            return
        if (
            data["last_updated"] + datetime.timedelta(seconds=8)
            < datetime.datetime.utcnow()
        ):
            self.bot.dispatch("level_up", message, data)

    # @commands.Cog.listener()
    # async def on_member_remove(self, member: discord.Member):
    #     if member.bot: return
    #     if member.guild.id != 785839283847954433: return
    #     guild: discord.Guild = member.guild
    #     try:
    #         ban = await guild.fetch_ban(member)
    #         if ban: return
    #     except discord.NotFound:
    #         pass
    #     member_data = await self.levels.get_member_level(member)
    #     if member_data['weekly'] < 10:
    #         if member_data['level'] > 5: return
    #         data = await self.bot.free.find(member.id)
    #         if data is None:
    #             data = {
    #                 "_id": member.id,
    #                 "total_ff": 1,
    #                 "banned": False,
    #                 "ban_days": 7,
    #                 "unbanAt": None,
    #             }
    #             await self.bot.free.insert(data)
    #         if data['total_ff'] == 1:
    #             data['unbanAt'] = datetime.datetime.utcnow() + datetime.timedelta(days=data['ban_days'])
    #         else:
    #             days = data['ban_days'] * data['total_ff']
    #             data['unbanAt'] = datetime.datetime.utcnow() + datetime.timedelta(days=days)
    #         await guild.ban(member, reason=f"Freeloaded after Heist. Total Freeloads: {data['total_ff']}")
    #         embed = discord.Embed(title="Freeloader Banned", description=f"", color=discord.Color.red())
    #         embed.description += f"**User:** {member.mention} | `{member.id}`\n"
    #         embed.description += f"**Total Freeloads:** {data['total_ff']}\n"
    #         embed.description += f"**Ban Duration:** {data['ban_days']} days\n"
    #         embed.description += f"**Unban in** <t:{round(data['unbanAt'].timestamp())}:R>\n"
    #         embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar)
    #         embed.set_footer(text="The Gambler's Kingdom", icon_url=guild.icon.url)
    #         await self.webhook.send(embed=embed)
    #         data['total_ff'] += 1
    #         data['banned'] = True
    #         await self.bot.free.update(data)

    @commands.Cog.listener()
    async def on_slash_command(self, message: discord.Message):
        if message.guild is None:
            return
        config = await self.levels.get_config(message.guild)
        if not config["enabled"]:
            return

        if not message._interaction:
            return
        user = message._interaction.user
        data = await self.levels.get_member_level(user)
        if (
            data["last_updated"] is None
            or data["last_updated"] + datetime.timedelta(seconds=8)
            < datetime.datetime.utcnow()
        ):
            pass
        else:
            return
        mutiplier = 1

        mutiplier += config["global_multiplier"]
        user_roles = [role.id for role in user.roles]
        if set(user_roles) & set(config["blacklist"]["roles"]):
            return
        if str(message.channel.id) in config["blacklist"]["channels"]:
            return

        if str(message.channel.id) in config["multipliers"]["channels"].keys():
            mutiplier += config["multipliers"]["channels"][str(message.channel.id)]

        for role in user_roles:
            if str(role) in config["multipliers"]["roles"].keys():
                mutiplier += config["multipliers"]["roles"][str(role)]

        expirience = 1
        expirience *= mutiplier
        data["xp"] += expirience
        data["weekly"] += 1
        data["last_updated"] = datetime.datetime.utcnow()
        level = await self.levels.count_level(data["xp"])
        if level > data["level"]:
            data["level"] = level
            roles = []
            for key, value in config["rewards"].items():
                if level >= int(key):
                    role = message.guild.get_role(value)
                    if role is None:
                        continue
                    roles.append(role)
            if len(roles) > 0:
                await user.add_roles(*roles)

            level_up_embed = discord.Embed(description="", color=self.bot.default_color)
            level_up_embed.set_thumbnail(
                url=user.avatar.url if user.avatar else user.default_avatar
            )
            level_up_embed.description += f"## Congratulations {user.mention}!\n you have leveled up to level {level}!"
            level_up_embed.set_footer(
                text="The Gambler's Kingdom",
                icon_url=message.guild.icon.url if message.guild.icon else None,
            )
            annouce = message.guild.get_channel(config["announcement_channel"])
            if annouce is None:
                return
            await annouce.send(embed=level_up_embed, content=user.mention)

        if data["weekly"] >= config["weekly"]["required_messages"]:
            role = message.guild.get_role(config["weekly"]["role"])
            if role is None:
                return
            if role in user.roles:
                return
            await user.add_roles(
                role, reason="Reached required messages for weekly role"
            )

    @commands.Cog.listener()
    async def on_level_up(self, message: discord.Message, data: dict):
        config = await self.levels.get_config(message.guild)
        if not config["enabled"]:
            return
        user_roles = [role.id for role in message.author.roles]
        if set(user_roles) & set(config["blacklist"]["roles"]):
            return
        if str(message.channel.id) in config["blacklist"]["channels"]:
            return

        multiplier = config["global_multiplier"]

        if str(message.channel.id) in config["multipliers"]["channels"].keys():
            multiplier += config["multipliers"]["channels"][str(message.channel.id)]

        for role in user_roles:
            if str(role) in config["multipliers"]["roles"].keys():
                multiplier += config["multipliers"]["roles"][str(role)]

        exprience = 1
        exprience *= multiplier

        data["xp"] += exprience
        data["weekly"] += 1
        data["last_updated"] = datetime.datetime.utcnow()
        level = await self.levels.count_level(data["xp"])
        if level > data["level"]:
            data["level"] = level
            roles = []
            for key, value in config["rewards"].items():
                if level >= int(key):
                    role = message.guild.get_role(value)
                    if role is None:
                        continue
                    roles.append(role)
            if len(roles) > 0:
                await message.author.add_roles(*roles)
            level_up_embed = discord.Embed(description="", color=self.bot.default_color)
            level_up_embed.set_thumbnail(
                url=message.author.avatar.url
                if message.author.avatar
                else message.author.default_avatar
            )
            level_up_embed.description += f"## Congratulations {message.author.mention}!\n you have leveled up to level {level}!"
            level_up_embed.set_footer(
                text="The Gambler's Kingdom",
                icon_url=message.guild.icon.url if message.guild.icon else None,
            )
            annouce = message.guild.get_channel(config["announcement_channel"])
            if annouce is None:
                return
            await annouce.send(embed=level_up_embed, content=message.author.mention)

        await self.levels.update_member_level(message.author, data)
        if data["weekly"] >= config["weekly"]["required_messages"]:
            role = message.guild.get_role(config["weekly"]["role"])
            if role is None:
                return
            if role in message.author.roles:
                return
            await message.author.add_roles(
                role, reason="Reached required messages for weekly role"
            )

    @app_commands.command(name="rank", description="View your rank card")
    @app_commands.checks.cooldown(1, 10, key=lambda i: (i.guild_id, i.user.id))
    async def rank(self, interaction: Interaction, member: discord.Member = None):
        await interaction.response.defer()
        member = member if member else interaction.user
        ranks = await self.levels.ranks.get_all()
        ranks = {
            i["_id"]: i for i in sorted(ranks, key=lambda x: x["xp"], reverse=True)
        }
        rank = int(list(ranks.keys()).index(member.id)) + 1
        level = ranks[member.id]["level"]
        exp = await self.levels.millify(ranks[member.id]["xp"])
        weekly = await self.levels.millify(ranks[member.id]["weekly"])
        card = await self.levels.create_rank_card(member, rank + 1, level, exp, weekly)

        with BytesIO() as image_binary:
            card.save(image_binary, "PNG")
            image_binary.seek(0)
            embed = discord.Embed()
            embed.color = self.bot.default_color
            embed.set_image(url="attachment://rank.png")
            await interaction.followup.send(
                file=discord.File(fp=image_binary, filename="rank.png"), embed=embed
            )

    @rank.error
    async def rank_error(self, interaction: Interaction, error):
        raise error

    @app_commands.command(
        name="leaderboard", description="View the server's leaderboard"
    )
    @app_commands.checks.cooldown(1, 300, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.choices(
        type=[
            app_commands.Choice(name="Exp", value="xp"),
            app_commands.Choice(name="Weekly", value="weekly"),
            app_commands.Choice(name="Level", value="level"),
        ]
    )
    async def leaderboard(self, interaction: Interaction, type: str):
        await interaction.response.defer()
        ranks = await self.levels.ranks.get_all()
        ranks = {
            i["_id"]: i for i in sorted(ranks, key=lambda x: x[type], reverse=True)
        }
        user_rank = list(ranks.keys()).index(interaction.user.id) + 1
        chunks = chunk(ranks.items(), 10)
        embeds = []
        for chunked in chunks:
            embed = discord.Embed(
                title=f"{interaction.guild.name}'s Leaderboard",
                description=f"**Leaderboard Type:** {type.capitalize()}\n",
                color=self.bot.default_color,
            )
            embed.set_thumbnail(
                url=interaction.guild.icon.url if interaction.guild.icon else None
            )
            embed.set_footer(
                text=f"Your Rank: {user_rank}",
                icon_url=interaction.user.avatar.url
                if interaction.user.avatar
                else interaction.user.default_avatar,
            )

            for i in chunked:
                i = dict(i[1])
                member = interaction.guild.get_member(i["_id"])
                if not isinstance(member, discord.Member):
                    continue
                if i["xp"] < 35:
                    exp = 0
                else:
                    exp = await self.levels.millify(i["xp"])
                if member.id == interaction.user.id:
                    embed.description += f" **{list(ranks.keys()).index(i['_id']) + 1}. {member.mention}** <:pin:1000719163851018340>\n"
                else:
                    embed.description += f" **{list(ranks.keys()).index(i['_id']) + 1}. {member.mention}**\n"
                embed.description += (
                    "-# "
                    + f"**Level:** {i['level']} | **Exp:** {exp} | **Weekly:** {i['weekly']}\n"
                )

            embeds.append(embed)

        await Paginator(interaction, embeds).start(
            embeded=True,
            timeout=60,
            hidden=False,
            quick_navigation=False,
            deffered=True,
        )

    @leaderboard.error
    async def leaderboard_error(self, interaction: Interaction, error):
        raise error

    @app_commands.command(name="set", description="Set a user's level")
    @app_commands.checks.has_permissions(administrator=True)
    async def set(self, interaction: Interaction, member: discord.Member, level: int):
        data = await self.levels.get_member_level(member)
        data["xp"] = await self.levels.count_xp(level)
        data["level"] = level
        await self.levels.update_member_level(member, data)
        await interaction.response.send_message(
            f"Succesfully set {member.mention}'s level to {level}"
        )
        config = await self.levels.get_config(member.guild)
        roles = []
        for key, value in config["rewards"].items():
            if level >= int(key):
                role = member.guild.get_role(value)
                if role is None:
                    continue
                roles.append(role)
        if len(roles) > 0:
            await member.add_roles(*roles)
        await self.levels.update_member_level(member, data)

    @app_commands.command(name="reset", description="Reset a user's level")
    @app_commands.checks.has_permissions(administrator=True)
    async def reset(self, interaction: Interaction, member: discord.Member):
        await self.levels.ranks.delete(member.id)
        del self.levels.level_cache[member.id]
        await interaction.response.send_message(f"Reset {member.mention}'s level")
        config = await self.levels.get_config(member.guild)
        roles = []
        for key, value in config["rewards"].items():
            role = member.guild.get_role(value)
            if role is None:
                continue
            roles.append(role)
        await member.remove_roles(*roles)
        await self.levels.update_member_level(
            member,
            {
                "xp": 0,
                "level": 0,
                "weekly": 0,
                "last_updated": datetime.datetime.utcnow(),
            },
        )

    @weekly.command(name="reset", description="Reset a server's weekly xp")
    @app_commands.checks.has_permissions(administrator=True)
    async def weekly_reset(self, interaction: Interaction):
        await interaction.response.send_message(
            embed=discord.Embed(description="Please wait... This may take a while"),
            ephemeral=True,
        )
        data = await self.levels.ranks.get_all()
        new_data = []
        for i in data:
            i["weekly"] = 0
            new_data.append(i)
            self.levels.level_cache[i["_id"]] = i
        await self.levels.ranks.bulk_update(new_data)
        config = await self.levels.get_config(interaction.guild)
        if config["weekly"]["required_messages"] != 0:
            role = interaction.guild.get_role(1128307039672737874)
            if role is None:
                return
            for member in interaction.guild.members:
                if role in member.roles:
                    await member.remove_roles(role, reason="Weekly reset")
                    await asyncio.sleep(0.5)
        await interaction.edit_original_response(
            content="Succesfully reset weekly xp", embed=None
        )


async def setup(bot):
    await bot.add_cog(Level(bot))
