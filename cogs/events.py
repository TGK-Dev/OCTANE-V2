import datetime
import discord
import asyncio
import re

from discord.ext import commands, tasks
from utils.db import Document


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.counter_task = self.update_member_counter.start()
        self.activiy_webhook = None
        self.vote_task_progress = False
        self.bot.whitelist = Document(bot.db, "whitelist")

    def cog_unload(self):
        self.counter_task.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        channel = self.bot.get_channel(1031514773310930945)
        for webhook in await channel.webhooks():
            if webhook.user.id == self.bot.user.id:
                self.activiy_webhook = webhook
        if not isinstance(self.activiy_webhook, discord.Webhook):
            avatar = await self.bot.user.avatar.read()
            self.activiy_webhook = await channel.create_webhook(
                name=self.bot.user.name, avatar=avatar
            )

    @tasks.loop(minutes=5)
    async def update_member_counter(self):
        guild = self.bot.get_guild(785839283847954433)
        member_count = guild.member_count
        channel = guild.get_channel(821747332327931995)
        number = re.findall(r"\d+", channel.name)
        number = int(number[0])
        if number != member_count:
            new_name = f"{channel.name.replace(str(number), str(member_count))}"
            await channel.edit(name=new_name)

    @update_member_counter.before_loop
    async def before_update_member_counter(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild:
            return

        if message.guild.id != 785839283847954433:
            return

        if message.webhook_id in [1216992114961940530]:
            await message.delete(delay=5)

        if message.channel.id == 1079670945171640360:
            self.bot.dispatch("dank_price_update", message)

        if message.author.id == 270904126974590976:
            if len(message.embeds) == 0:
                return
            embed = message.embeds[0]
            if not isinstance(embed, discord.Embed):
                return
            if embed.description is None:
                return
            if embed.description.startswith(
                "Successfully paid"
            ) and embed.description.endswith("from the server's pool!"):
                command_message = await message.channel.fetch_message(
                    message.reference.message_id
                )
                if command_message._interaction is None:
                    return
                if command_message._interaction.name != "serverevents payout":
                    return

                embed = command_message.embeds[0].to_dict()
                winner = re.findall(r"<@!?\d+>", embed["description"])
                prize = re.findall(r"\*\*(.*?)\*\*", embed["description"])[0]
                emojis = list(set(re.findall(":\w*:\d*", prize)))
                for emoji in emojis:
                    prize = prize.replace(emoji, "", 100)
                    prize = prize.replace("<>", "", 100)
                    prize = prize.replace("<a>", "", 100)
                    prize = prize.replace("  ", " ", 100)

                log_embed = discord.Embed(
                    title="Server Events Payout",
                    description="",
                    color=self.bot.default_color,
                )
                log_embed.description += f"**Winner**: {winner[0]}\n"
                log_embed.description += f"**Prize**: {prize}\n"
                log_embed.description += (
                    f"**Paid by**: {command_message._interaction.user.mention}\n"
                )
                link_view = discord.ui.View()
                link_view.add_item(
                    discord.ui.Button(
                        label="Go to Payout Message", url=command_message.jump_url
                    )
                )
                log_channel = self.bot.get_channel(1076586539368333342)
                await log_channel.send(embed=log_embed, view=link_view)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if not before.guild or before.guild.id != 785839283847954433:
            return
        if after.author.id != 270904126974590976:
            return

        if after.channel.id not in [
            812711254790897714,
            1210094990315753472,
            1116295238584111155,
            1086323496788963328,
        ]:
            return
        if len(after.embeds) == 0:
            return
        embed: discord.Embed = after.embeds[0]

        if not embed.description.startswith("Successfully donated "):
            return

        prize = re.findall(r"\*\*(.*?)\*\*", embed.description)[0]
        emojis = list(set(re.findall(":\w*:\d*", prize)))
        for emoji in emojis:
            prize = prize.replace(emoji, "", 100)
            prize = prize.replace("<>", "", 100)
            prize = prize.replace("<a>", "", 100)
            prize = prize.replace("  ", " ", 100)

        donor = after._interaction.user
        await after.reply(
            f"{donor.mention} successfully donated **{prize}** to the server pool!",
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        if guild.owner_id not in self.bot.owner_ids:
            whitelist = await self.whitelist.find(guild.id)
            if not whitelist:
                await guild.leave()

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return

        elif isinstance(error, commands.CommandOnCooldown):
            return await ctx.send(
                f"This command is on cooldown for {error.retry_after:.2f} seconds"
            )

        elif isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send(f"Missing required argument {error.param.name}")

        elif isinstance(error, commands.BadArgument):
            return await ctx.send(f"Bad argument {error.param.name}")

        elif isinstance(error, commands.MissingPermissions):
            return await ctx.send("You don't have permission to use this command")

        elif isinstance(error, commands.BotMissingPermissions):
            return await ctx.send("I don't have permission to use this command")

        elif isinstance(error, commands.CheckFailure):
            return await ctx.send("You don't have permission to use this command")

        elif isinstance(error, commands.CommandInvokeError):
            return await ctx.send(
                f"An error occured while executing this command\n```\n{error}\n```"
            )

        else:
            embed = discord.Embed(
                color=0xE74C3C,
                description=f"<:dnd:840490624670892063> | Error: `{error}`",
            )
            await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_presence_update(self, before, after):
        if before.guild.id != 785839283847954433:
            return
        supporter_role = before.guild.get_role(992108093271965856)
        if len(after.activities) <= 0 and supporter_role in after.roles:
            await after.remove_roles(supporter_role, reason="No longer supporting")
            return
        await asyncio.sleep(5)

        for activity in after.activities:
            try:
                if activity.type == discord.ActivityType.custom:
                    if ".gg/tgk" in activity.name.lower():
                        if supporter_role in after.roles:
                            return
                        embed = discord.Embed(
                            description=f"Thanks for supporting the The Gambler's Kingdom\n\nYou have been given the {supporter_role.mention} role",
                            color=supporter_role.color,
                        )
                        embed.set_author(
                            name=f"{after.global_name}({after.id})",
                            icon_url=after.avatar.url
                            if after.avatar
                            else after.default_avatar,
                        )
                        embed.set_footer(
                            text=self.bot.user.name, icon_url=self.bot.user.avatar.url
                        )
                        embed.timestamp = datetime.datetime.now()
                        embed.set_thumbnail(
                            url="https://cdn.discordapp.com/emojis/869579480509841428.gif?v=1"
                        )
                        await self.activiy_webhook.send(embed=embed)
                        await after.add_roles(supporter_role)
                        return

                    elif ".gg/tgk" not in activity.name.lower():
                        if supporter_role in after.roles:
                            await after.remove_roles(supporter_role)
                        return
            except Exception:
                pass

    @commands.Cog.listener()
    async def on_member_ban(
        self, guild: discord.Guild, user: discord.User | discord.Member
    ):
        if guild.id != 785839283847954433:
            return
        ban = await guild.fetch_ban(user)
        if "no appeal" in ban.reason.lower():
            appeal_server = self.bot.get_guild(988761284956799038)
            if appeal_server is None:
                return
            await appeal_server.ban(
                user, reason="Banned in main server with no appeal tag"
            )
            return

    @commands.Cog.listener()
    async def on_automod_action(self, execution: discord.AutoModAction):
        if (
            execution.rule_id in [1082688649696653445]
            and execution.action.type
            == discord.AutoModRuleActionType.send_alert_message
        ):
            content = execution.content
            user = execution.guild.get_member(execution.user_id)
            if "@here" in content or "@everyone" in content:
                try:
                    await execution.guild.fetch_ban(user)
                    return
                except discord.NotFound:
                    pass

                try:
                    await user.send(
                        f"You are banned from {execution.guild.name} because your account was compromised. Please appeal in the appeal server: https://discord.gg/aWhc6mFCJV"
                    )
                except discord.HTTPException:
                    pass

                await execution.guild.ban(user, reason="Hacked / Compromised Account")


async def setup(bot):
    await bot.add_cog(Events(bot))
