import discord
import datetime
from io import BytesIO
from discord import Interaction
from discord.ui import View, button


class TyperaceView(View):
    def __init__(self, data, image: BytesIO):
        self.data = data
        self.image = image
        super().__init__(timeout=300)

    async def interaction_check(self, interaction: Interaction):
        if interaction.channel.id not in interaction.client.type_race_cache.keys():
            await interaction.response.send_message(
                "This is not a typerace message", ephemeral=True
            )
            return False
        return True

    @button(label="Start", style=discord.ButtonStyle.green)
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = interaction.client.type_race_cache[interaction.channel.id]
        if not data:
            return await interaction.followup.send(
                "This is not a typerace message", ephemeral=True
            )
        if interaction.user.id != data["host"]:
            return await interaction.followup.send(
                "Only the host can start the typerace", ephemeral=True
            )
        embed = discord.Embed(
            title="Typerace",
            description="Type the quote as fast as you can",
            color=discord.Color.random(),
        )
        embed.set_image(url="attachment://image.png")
        button.disabled = True
        button.label = "Started"
        await interaction.response.edit_message(
            embed=embed,
            attachments=[discord.File(self.image, filename="image.png")],
            view=self,
        )
        data["start"] = datetime.datetime.utcnow()
        data["started"] = True
        interaction.client.type_race_cache[interaction.channel.id] = data

    @button(label="Leaderboard", style=discord.ButtonStyle.blurple)
    async def leaderboard(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_message("Please wait...", ephemeral=True)
        data = interaction.client.type_race_cache[interaction.channel.id][
            "participants"
        ]
        if not data:
            return await interaction.followup.send(
                "This is not a typerace message", ephemeral=True
            )
        if len(data) == 0:
            await interaction.followup.send(
                "No one has completed the typerace yet", ephemeral=True
            )
            return
        data = sorted(
            data.items(), key=lambda x: (x[1]["acuracy"], -x[1]["time"]), reverse=True
        )
        embed = discord.Embed(
            title="Typerace Leaderboard",
            color=interaction.client.default_color,
            description="",
        )
        for i in range(len(data)):
            user = interaction.guild.get_member(data[i][0])
            if user is None:
                continue
            embed.description += f"{i+1}. {user.mention} - {data[i][1]['acuracy']}% - {data[i][1]['wpm']} wpm\n"
        await interaction.edit_original_response(embed=embed, content=None)

    @button(label="End", style=discord.ButtonStyle.red)
    async def end(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = interaction.client.type_race_cache[interaction.channel.id]
        if not data:
            return await interaction.followup.send(
                "This is not a typerace message", ephemeral=True
            )
        if interaction.user.id != data["host"]:
            return await interaction.response.send_message(
                "Only the host can end the typerace", ephemeral=True
            )
        for button in self.children:
            button.disabled = True
        await interaction.response.edit_message(view=self)
        data = data["participants"]
        if len(data) == 0:
            await interaction.followup.send(
                "No one has completed the typerace yet", ephemeral=True
            )
            return
        data = sorted(
            data.items(), key=lambda x: (x[1]["acuracy"], -x[1]["time"]), reverse=True
        )
        embed = discord.Embed(
            title="Typerace Leaderboard",
            color=interaction.client.default_color,
            description="",
        )
        for i in range(len(data)):
            user = interaction.guild.get_member(data[i][0])
            if user is None:
                continue
            if i == 0:
                embed.description += f"### 🥇 {user.mention} - {data[i][1]['acuracy']}% - {data[i][1]['wpm']} wpm\n"
            elif i == 1:
                embed.description += f"### 🥈 {user.mention} - {data[i][1]['acuracy']}% - {data[i][1]['wpm']} wpm\n"
            elif i == 2:
                embed.description += f"### 🥉 {user.mention} - {data[i][1]['acuracy']}% - {data[i][1]['wpm']} wpm\n"
            else:
                embed.description += f"{i+1}. {user.mention} - {data[i][1]['acuracy']}% - {data[i][1]['wpm']} wpm\n"
        await interaction.followup.send(embed=embed, ephemeral=False)

        try:
            interaction.client.type_race_cache.pop(interaction.channel.id)
        except Exception:
            return
