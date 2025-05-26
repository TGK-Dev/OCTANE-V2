import discord
from discord.ui.view import View


class QueueView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Join Event",
        style=discord.ButtonStyle.green,
        custom_id="join_queue",
    )
    async def join_event(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """
        Button to join the event queue.
        """

        data = await interaction.client._team.queues.find(interaction.user.id)
        if data:
            await interaction.response.send_message(
                "You are already in the queue.", ephemeral=True
            )
            return
        await interaction.client._team.queues.insert(
            {
                "_id": interaction.user.id,
            }
        )
        await interaction.response.send_message(
            "You have joined the event queue.", ephemeral=True
        )
