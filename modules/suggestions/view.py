import discord
from discord import Interaction
from utils.views.selects import Select_General
from utils.views.modal import General_Modal


class Vote(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def interaction_check(self, interaction: Interaction[discord.Client]):
        config = await interaction.client.sugconfig.find({"_id": interaction.guild_id})
        if not config:
            config = {
                "_id": interaction.guild_id,
                "status": "active",
                "banned_users": [],
            }
            await interaction.client.sugconfig.insert(config)

        if config["status"] == "inactive":
            await interaction.response.send_message(
                "Suggestion system is disabled", ephemeral=True
            )
            return False
        if interaction.user.id in config["banned_users"]:
            await interaction.response.send_message(
                "You are banned from using the suggestion system", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(
        emoji="<:tgk_uparrow:952869374811844659>",
        custom_id="vote:upvote",
        style=discord.ButtonStyle.gray,
    )
    async def upvote(self, interaction: Interaction, button: discord.ui.Button):
        if len(interaction.message.embeds) < 0:
            return await interaction.response.send_message(
                "Invalid message", ephemeral=True
            )
        embed = interaction.message.embeds[0]
        if embed.footer.text.lower().startswith("phrase"):
            db = interaction.client.phreases
        elif embed.footer.text.lower().startswith("location"):
            db = interaction.client.locations
        else:
            return await interaction.response.send_message(
                "Invalid message", ephemeral=True
            )
        data = await db.find(interaction.message.id)
        if not data:
            return await interaction.response.send_message(
                "Invalid message", ephemeral=True
            )

        if data["status"] in ["rejected", "approved", "closed"]:
            return await interaction.response.send_message(
                "This suggestion is closed", ephemeral=True, delete_after=5
            )

        if interaction.user.id in data["upvoters"]:
            data["upvotes"] -= 1
            data["upvoters"].remove(interaction.user.id)
        else:
            data["upvotes"] += 1
            data["upvoters"].append(interaction.user.id)
        if interaction.user.id in data["downvoters"]:
            data["downvotes"] -= 1
            data["downvoters"].remove(interaction.user.id)

        await db.update(data)
        if len(embed.fields) == 2:
            embed.clear_fields()
            embed.add_field(
                name="Upvotes", value=f"```{data['upvotes']}```", inline=True
            )
            embed.add_field(
                name="Downvotes", value=f"```{data['downvotes']}```", inline=True
            )
        else:
            embed.set_field_at(
                1,
                name="Upvotes",
                value=f"```{data['upvotes']}```",
                inline=True,
            )
            embed.set_field_at(
                2,
                name="Downvotes",
                value=f"```{data['downvotes']}```",
                inline=True,
            )

        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(
        emoji="<:tgk_downarrow:952869754916450354>",
        custom_id="vote:downvote",
        style=discord.ButtonStyle.gray,
    )
    async def downvote(self, interaction: Interaction, button: discord.ui.Button):
        if len(interaction.message.embeds) < 0:
            return await interaction.response.send_message(
                "Invalid message", ephemeral=True
            )
        embed = interaction.message.embeds[0]
        if embed.footer.text.lower().startswith("phrase"):
            db = interaction.client.phreases
        elif embed.footer.text.lower().startswith("location"):
            db = interaction.client.locations
        else:
            return await interaction.response.send_message(
                "Invalid message", ephemeral=True
            )
        data = await db.find(interaction.message.id)
        if not data:
            return await interaction.response.send_message(
                "Invalid message", ephemeral=True
            )

        if data["status"] in ["rejected", "approved", "closed"]:
            return await interaction.response.send_message(
                "This suggestion is closed", ephemeral=True, delete_after=5
            )

        if interaction.user.id in data["downvoters"]:
            data["downvotes"] -= 1
            data["downvoters"].remove(interaction.user.id)
        else:
            data["downvotes"] += 1
            data["downvoters"].append(interaction.user.id)
        if interaction.user.id in data["upvoters"]:
            data["upvotes"] -= 1
            data["upvoters"].remove(interaction.user.id)

        await db.update(data)
        if len(embed.fields) == 2:
            embed.clear_fields()
            embed.add_field(
                name="Upvotes", value=f"```{data['upvotes']}```", inline=True
            )
            embed.add_field(
                name="Downvotes", value=f"```{data['downvotes']}```", inline=True
            )
        else:
            embed.set_field_at(
                1,
                name="Upvotes",
                value=f"```{data['upvotes']}```",
                inline=True,
            )
            embed.set_field_at(
                2,
                name="Downvotes",
                value=f"```{data['downvotes']}```",
                inline=True,
            )

        await interaction.response.edit_message(embed=embed)


    @discord.ui.button(
        emoji="<:TGK_Settings:1306539203928002560>",
        custom_id="vote:settings",
        style=discord.ButtonStyle.gray,
    )
    async def settings(self, interaction: Interaction, button: discord.ui.Button):
        if len(interaction.message.embeds) < 0:
            return await interaction.response.send_message(
                "Invalid message", ephemeral=True
            )
        embed = interaction.message.embeds[0]
        if embed.footer.text.lower().startswith("phrase"):
            db = interaction.client.phreases
        elif embed.footer.text.lower().startswith("location"):
            db = interaction.client.locations
        else:
            return await interaction.response.send_message(
                "Invalid message", ephemeral=True
            )
        data = await db.find(interaction.message.id)

        view = discord.ui.View()
        view.value = None
        option = [
            discord.SelectOption(
                label="Approve",
                value="approved",
                description="Approve suggestion",
                emoji="<:tgk_active:1082676793342951475>",
            ),
            discord.SelectOption(
                label="Close",
                value="closed",
                description="Close suggestion",
                emoji="<:tgk_lock:1072851190213259375>",
            ),
            discord.SelectOption(
                label="Reject",
                value="rejected",
                description="Reject suggestion",
                emoji="<:tgk_deactivated:1082676877468119110>",
            ),
            discord.SelectOption(
                label="Close With Reason",
                value="closed_with_reason",
                description="Close suggestion with reason",
            ),
            discord.SelectOption(
                label="Approve With Reason",
                value="approved_with_reason",
                description="Approve suggestion with reason",
            ),
            discord.SelectOption(
                label="Reject With Reason",
                value="rejected_with_reason",
                description="Reject suggestion with reason",
            ),
        ]
        view.select = Select_General(
            max_values=1, placeholder="Select an option", options=option
        )
        view.add_item(view.select)

        await interaction.response.send_message(
            view=view,
            ephemeral=True,
        )

        await view.wait()
        if not view.value:
            return

        if view.select.values[0].lower().endswith("reason"):
            modal = General_Modal(title="Reason for action", interaction=interaction)
            modal.reason = discord.ui.TextInput(
                label="Reason",
                placeholder="Reason for action",
                required=True,
                style=discord.TextStyle.paragraph,
            )
            modal.add_item(modal.reason)

            await view.select.interaction.response.send_modal(modal)
            await modal.wait()
            if not modal.value:
                return
            data["status_reason"] = modal.reason.value
            data["status_by"] = interaction.user.id
            data["status"] = view.select.values[0].replace("_with_reason", "")
            await modal.interaction.response.send_message(
                "done", delete_after=0.5, ephemeral=True
            )
        else:
            data["status"] = view.select.values[0]
            data["status_by"] = interaction.user.id
            await view.select.interaction.response.send_message(
                "done", ephemeral=True, delete_after=0.5
            )

        await db.update(data)

        value = ""
        if data["status_reason"]:
            value = f"Reason: {data['status_reason']}"
        else:
            value = "No reason provided"

        if len(embed.fields) == 2:
            embed.insert_field_at(
                0,
                name=f"{data['status'].capitalize()} By {interaction.user.name}",
                value=f"{value}",
                inline=False,
            )
        else:
            embed.set_field_at(
                0,
                name=f"{data['status'].capitalize()} By {interaction.user.name}",
                value=f"{value}",
                inline=False,
            )

        if data["status"] == "approved":
            embed.color = discord.Color.green()
        elif data["status"] == "rejected":
            embed.color = discord.Color.red()
        elif data["status"] == "closed":
            embed.color = discord.Color.yellow()

        await interaction.message.edit(embed=embed, view=self)
        await interaction.delete_original_response()
