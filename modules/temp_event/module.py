import json
import discord
from discord.ext import commands
import re

from utils.dank import DonationsInfo


# regex to find anything btw ** and ** parenthesis


class TempEvent(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dev_chl = self.bot.get_channel(1366375121752817704)

    @commands.Cog.listener()
    async def on_socket_raw_receive(self, msg):
        msg = json.loads(msg)

        if msg.get("t") == "MESSAGE_CREATE":
            if msg["d"]["author"]["id"] not in [
                "270904126974590976",
                "488614633670967307",
            ]:
                return

            if msg["d"].get("interaction_metadata"):
                if msg["d"]["interaction_metadata"].get("name"):
                    if (
                        msg["d"]["interaction_metadata"]["name"]
                        == "serverevents payout"
                    ):
                        self.bot.dispatch("serverevents_payout", msg)
            else:
                return

        if msg.get("t") == "MESSAGE_UPDATE":
            if msg["d"]["author"]["id"] not in [
                "270904126974590976",
                "488614633670967307",
            ]:
                return

            if msg["d"].get("interaction"):
                if (
                    msg["d"]["interaction"].get("name")
                    and msg["d"]["interaction"].get("name") == "serverevents donate"
                ):
                    content = msg["d"]["components"][0]["components"][0]["content"]
                    if not content.startswith("Successfully donated"):
                        return
                    channel = self.bot.get_channel(int(msg["d"]["channel_id"]))
                    if not channel:
                        try:
                            channel = await self.bot.fetch_channel(
                                int(msg["d"]["channel_id"])
                            )
                        except discord.NotFound:
                            return
                    guild: discord.Guild = channel.guild
                    donor = guild.get_member(int(msg["d"]["interaction"]["user"]["id"]))
                    if not donor:
                        try:
                            donor = await guild.fetch_member(
                                int(msg["d"]["interaction"]["user"]["id"])
                            )
                        except discord.NotFound:
                            return

                    reg = re.compile(
                        r"\*\*?(?:⏣\s*)?([\d,]+)(?:\s*<[^>]+>)?\s*([\w ]+)?\*\*?"
                    )
                    donation_info_raw = reg.search(content)
                    if not donation_info_raw:
                        return
                    ammout = int(
                        donation_info_raw.group(1)
                        .replace(",", "", 100)
                        .replace(" ", "", 100)
                    )
                    donation_info: DonationsInfo = DonationsInfo(
                        donor=donor,
                        quantity=ammout,
                        items=donation_info_raw.group(2),
                    )
                    donation_info.message = discord.Message(
                        state=self.bot._connection,
                        channel=channel,
                        data=msg["d"],
                    )

                    self.bot.dispatch("serverevents_donate", donation_info)

    # @commands.Cog.listener()
    # async def on_serverevents_donate(self, donation_info: DonationsInfo):
    #     if not donation_info.message:
    #         return
    #     chl = donation_info.message.channel
    #     await chl.send(f"Donation Info: {donation_info}")

    @commands.Cog.listener()
    async def on_serverevents_payout(self, msg, **kwargs):
        pass

    @commands.command()
    @commands.is_owner()
    async def ptest(self, ctx: commands.Context, member: discord.User):
        """
        Test the payout system.
        """

        def check(msg):
            print("checking payout")

            if not msg["d"]["components"][0]["components"][0]["content"].startswith(
                "Successfully paid"
            ):
                return False
            print("payout check passed")
            print("applying regex")
            reg = re.compile(r"Successfully paid (.*?) (\*\*.*?\*\*)")
            donation_info_raw = reg.findall(
                msg["d"]["components"][0]["components"][0]["content"]
            )
            print(donation_info_raw)
            donation_info = {
                "user": donation_info_raw[0][0],
                "item": donation_info_raw[0][1],
            }
            print(donation_info)
            if donation_info["user"] != member.display_name:
                return False
            return True

        await ctx.send("waiting for payout...")
        msg = await self.bot.wait_for("serverevents_payout", check=check, timeout=100)
        print(msg)
        if msg:
            message = discord.Message(
                state=self.bot._connection,
                channel=ctx.channel,
                data=msg["d"],
            )
            await message.reply(
                "Payout Verified",
            )
            await message.add_reaction("✅")
        else:
            await ctx.send("Payout not received")


async def setup(bot):
    await bot.add_cog(TempEvent(bot))
    print("TempEvent cog loaded.")