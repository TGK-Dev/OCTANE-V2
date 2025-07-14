from typing import List
import discord
import datetime
from discord import app_commands
from discord.ext import commands, tasks
from utils.transformer import TimeConverter, DMCConverter
from utils.db import Document
from .view import RiddleView
import random


@app_commands.guild_only()
@app_commands.default_permissions(manage_messages=True)
@app_commands.allowed_installs(guilds=True, users=False)
class Riddle(commands.GroupCog, name="riddle"):
    def __init__(self, bot):
        self.bot = bot
        self.bot.riddle = Document(bot.db, "riddle")
        self.bot.add_view(RiddleView())
        self.check_riddles.start()

    async def item_autocomplete(
        self, interaction: discord.Interaction, string: str
    ) -> List[app_commands.Choice[str]]:
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

    @tasks.loop(seconds=5)
    async def check_riddles(self):
        """Check for riddles that have ended and process entries."""
        datas = await self.bot.riddle.find_many_by_custom(
            filter_dict={"ends_at": {"$lt": discord.utils.utcnow()}},
        )
        for data in datas:
            if data["message_id"] is None:
                continue
            message: discord.Message = await self.bot.get_channel(
                data["channel_id"]
            ).fetch_message(data["message_id"])
            if not message:
                continue

            if len(data["entries"]) < data["winners"]:
                embed = discord.Embed(
                    title="Riddle Giveaway Ended",
                    description=f"The riddle giveaway for **{data['riddle']}** has ended, not enough entries were made to select a winner.",
                    color=discord.Color.red(),
                )
                await message.edit(
                    embed=embed, view=None, content="**Riddle Giveaway Ended**"
                )
                await self.bot.riddle.delete(data["_id"])
                continue

            winners = []
            while len(winners) < data["winners"]:
                winner_id = random.choice(data["entries"])
                if winner_id not in winners:
                    winners.append(winner_id)
            winners_mentions = ", ".join(f"<@{winner_id}>" for winner_id in winners)
            embed = message.embeds[0]
            embed.description += f"\n\n**Winners:** {winners_mentions}"

            await message.edit(
                embed=embed, view=None, content="**Riddle Giveaway Ended**"
            )
            host = message.guild.get_member(data["host"])
            if host:
                host_embed = discord.Embed(
                    title="Your Riddle Giveaway Ended",
                    description=(
                        f"Your riddle giveaway for **{data['riddle']}** has ended.\n"
                        f"**Winners:** {winners_mentions}\n"
                        f"[Jump to message]({message.jump_url})\n"
                        "Please queue the payouts manually."
                    ),
                    color=discord.Color.green(),
                )
                await host.send(embed=host_embed)

                for winner_id in winners:
                    winner = message.guild.get_member(winner_id)
                    if winner:
                        try:
                            winner_embed = discord.Embed(
                                title="Congratulations!",
                                description=(
                                    f"{winner.mention}, you have won the riddle giveaway for **{data['riddle']}**!\n"
                                    f"You have won: {data['prize']}.\n"
                                    f"[Jump to message]({message.jump_url})"
                                ),
                                color=discord.Color.gold(),
                            )
                            await winner.send(embed=winner_embed)
                        except discord.Forbidden:
                            continue
            await self.bot.riddle.delete(data["_id"])

    @check_riddles.before_loop
    async def before_check_riddles(self):
        await self.bot.wait_until_ready()

    gaw = app_commands.Group(name="gaw", description="Gaw commands for Riddle module")

    @gaw.command(name="start", description="Start a Gaw with a riddle")
    @app_commands.describe(
        time="Time in seconds for the Gaw to run",
        winners="Number of winners for the Gaw",
        riddle="The riddle to be solved",
        answer="The answer to the riddle",
        quantity="The quantity of the reward",
        item="The item to be rewarded",
    )
    @app_commands.autocomplete(item=item_autocomplete)
    async def start_gaw(
        self,
        interaction: discord.Interaction,
        time: app_commands.Transform[int, TimeConverter],
        winners: int,
        riddle: str,
        answer: str,
        quantity: app_commands.Transform[int, DMCConverter],
        item: str = None,
    ):
        if not interaction.guild:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
            return
        if interaction.guild.id not in [785839283847954433, 999551299286732871]:
            await interaction.response.send_message(
                "This command can only be used in the specified servers.",
                ephemeral=True,
            )
            return

        if time <= 0:
            await interaction.response.send_message(
                "Time must be greater than 0 seconds.", ephemeral=True
            )
            return

        if item:
            prize = f"{quantity}x {item}"
        else:
            prize = f"⏣ {quantity:,}"

        ends = discord.utils.utcnow() + datetime.timedelta(seconds=time)
        embed = discord.Embed(
            title=prize, description="", color=interaction.client.default_color
        )

        embed.description += f"**Ends in: <t:{int(ends.timestamp())}:R> (<t:{int(ends.timestamp())}:t>)**\n"
        embed.description += f"**Hosted by:** {interaction.user.mention}\n"

        riddle_embed = discord.Embed(
            description=f"**Riddle:**\n{riddle}", color=discord.Color.blurple()
        )
        riddle_embed.set_footer(
            text="Submit the correct answer below to enter the giveaway!"
        )
        riddle_embed.timestamp = ends

        data = {
            "host": interaction.user.id,
            "riddle": riddle,
            "answer": answer.lower(),
            "quantity": quantity,
            "winners": winners,
            "prize": prize,
            "ends_at": ends,
            "entries": [],
            "guild": interaction.guild.id,
            "channel_id": interaction.channel.id,
            "message_id": None,  # This will be set when the message is sent
        }

        await interaction.response.send_message(
            "Riddle Gaw started!", ephemeral=True, delete_after=2
        )

        msg = await interaction.channel.send(
            embeds=[embed, riddle_embed],
            content="<a:TGK_TADA:1250113598835920936> **GIVEAWAY STARTED** <a:TGK_TADA:1250113598835920936>",
            view=RiddleView(),
        )
        data["message_id"] = msg.id
        data["_id"] = msg.id
        await self.bot.riddle.insert(data)


async def setup(bot):
    await bot.add_cog(
        Riddle(bot),
        guilds=[
            discord.Object(id=785839283847954433),
            discord.Object(id=999551299286732871),
        ],
    )
    print("Riddle module loaded successfully.")
