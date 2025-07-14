import datetime
import discord
from discord.ui import View


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
            await modal.interacton.response.send_message(
                f"Congratulations {interaction.user.mention}, you answered the riddle correctly! You have successfully entered the Giveaway.",
                ephemeral=True,
            )
        else:
            await modal.interacton.response.send_message(
                f"Sorry {interaction.user.mention}, your answer is incorrect. Please try again.",
                ephemeral=True,
            )

        await interaction.client.riddle.update(data)
