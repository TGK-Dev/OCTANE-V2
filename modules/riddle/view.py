import datetime
import discord
from discord.ui import View
from utils.paginator import Paginator
from utils.converters import chunk


class Model(discord.ui.Modal, title="Riddle Answer"):
    def __init__(self):
        super().__init__()
        self.ans = discord.ui.TextInput(
            label="Enter your answer",
            placeholder="Type your answer here...",
            required=True,
            style=discord.TextStyle.short,
        )
        self.add_item(self.ans)
        self.value = self.ans
        self.interacton = None

    async def on_submit(self, interaction: discord.Interaction):
        self.value = self.ans.value
        self.interacton = interaction
        self.stop()


class RiddleView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.children[1].disabled = True

    @discord.ui.button(
        emoji="<a:TGK_TADA:1250113598835920936>",
        style=discord.ButtonStyle.gray,
        custom_id="riddle_answer",
    )
    async def answer_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        data = await interaction.client.riddle.find(interaction.message.id)
        if not data:
            await interaction.response.send_message(
                "This riddle has already been answered or does not exist.",
                ephemeral=True,
            )
            return
        if discord.utils.utcnow() > data["ends_at"].replace(
            tzinfo=datetime.timezone.utc
        ):
            await interaction.response.send_message(
                "This riddle has already ended.", ephemeral=True
            )
            return
        if interaction.user.id in data["entries"]:
            await interaction.response.send_message(
                "You have already answered this riddle.", ephemeral=True
            )
            return
        modal = Model()
        await interaction.response.send_modal(modal)
        await modal.wait()
        if not modal.value:
            await interaction.followup.send(
                "You did not enter an answer.", ephemeral=True
            )
            return
        answer = modal.value.lower()
        if answer == data["answer"]:
            data["entries"].append(interaction.user.id)
            try:
                self.children[1].disabled = False
                self.children[1].label = len(data["entries"])
            except Exception:
                pass

            await modal.interacton.response.edit_message(view=self)
            await modal.interacton.followup.send(
                content=f"Congratulations {interaction.user.mention}, you answered the riddle correctly! You have successfully entered the Giveaway.",
                ephemeral=True,
            )
        else:
            await modal.interacton.response.send_message(
                f"Sorry {interaction.user.mention}, your answer is incorrect. Please try again.",
                ephemeral=True,
            )

        await interaction.client.riddle.update(data)

    @discord.ui.button(
        label=None,
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_people_group:1369679193754832957>",
        custom_id="giveaway:Entries",
        disabled=True,
    )
    async def entries_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        data = await interaction.client.riddle.find(interaction.message.id)
        if not data:
            await interaction.response.send_message(
                "This riddle has already been answered or does not exist.",
                ephemeral=True,
            )
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        embeds = []
        chunked_entries = chunk(data["entries"], 10)
        for i, chunks in enumerate(chunked_entries):
            embed = discord.Embed(
                title=f"Riddle Entries - Page {i + 1}",
                description="\n".join(
                    f"{interaction.client.get_user(user_id).mention}"
                    for user_id in chunks
                ),
                color=discord.Color.blue(),
            )
            embeds.append(embed)

        await Paginator(interaction=interaction, pages=embeds).start(
            embeded=True, quick_navigation=False, deffered=True, hidden=True
        )
