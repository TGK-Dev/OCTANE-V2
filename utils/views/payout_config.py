import discord
from .selects import Channel_select, Role_select

class Config_view(discord.ui.View):
    def __init__(self, data: dict, message: discord.Message=None):
        self.data = data
        self.message = message
        super().__init__(timeout=120)
    
    @discord.ui.button(label="Queue Channel", style=discord.ButtonStyle.gray, emoji="<:channel:1017378607863181322>")
    async def queue_channel(self, interaction: discord.Interaction, button: discord.ui.Button):

        view = discord.ui.View()
        view.value = False
        view.select = Channel_select("select new queue channel", max_values=1, min_values=1, disabled=False, channel_types=[discord.ChannelType.text])
        view.add_item(view.select)

        await interaction.response.send_message(content="Select a new channel from the dropdown menu below", view=view, ephemeral=True)
        await view.wait()

        if view.value:

            self.data["queue_channel"] = view.select.values[0].id
            await view.select.interaction.response.edit_message(content="Suscessfully updated queue channel", view=None)
            embed = interaction.message.embeds[0]
            embed.set_field_at(0, name="Queue Channel", value=view.select.values[0].mention)
            await interaction.message.edit(embed=embed)
            await interaction.client.payout_config.update(self.data)
        else:
            await interaction.edit_original_response(content="No channel selected", view=None)
    
    @discord.ui.button(label="Log Channel", style=discord.ButtonStyle.gray, emoji="<:channel:1017378607863181322>")
    async def log_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
            
            view = discord.ui.View()
            view.value = False
            view.select = Channel_select("select new log channel", max_values=1, min_values=1, disabled=False, channel_types=[discord.ChannelType.text])
            view.add_item(view.select)
    
            await interaction.response.send_message(content="Select a new channel from the dropdown menu below", view=view, ephemeral=True)
            await view.wait()
    
            if view.value:
    
                self.data["log_channel"] = view.select.values[0].id
                await view.select.interaction.response.edit_message(content="Suscessfully updated log channel", view=None)
                embed = interaction.message.embeds[0]
                embed.set_field_at(1, name="Log Channel", value=view.select.values[0].mention)
                await interaction.message.edit(embed=embed)
                await interaction.client.payout_config.update(self.data)
            else:
                await interaction.edit_original_response(content="No channel selected", view=None)
    
    @discord.ui.button(label="Manager Role", style=discord.ButtonStyle.gray, emoji="<:role:1017378607863181322>", row=1)
    async def manager_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View()
        view.value = False
        view.select = Role_select("select new manager role", max_values=10, min_values=1, disabled=False)
        view.add_item(view.select)

        await interaction.response.send_message(content="Select a new role from the dropdown menu below", view=view, ephemeral=True)
        await view.wait()

        if view.value:
                added = []
                removed = []
                for ids in view.select.values:
                    if ids.id not in self.data["manager_roles"]:
                        self.data["manager_roles"].append(ids.id)
                        added.append(ids.mention)
                    else:
                        self.data["manager_roles"].remove(ids.id)
                        removed.append(ids.mention)
                await view.select.interaction.response.edit_message(content=f"Suscessfully updated manager roles\nAdded: {', '.join(added)}\nRemoved: {', '.join(removed)}", view=None)

                embed = interaction.message.embeds[0]
                embed.set_field_at(2, name="Manager Roles", value=", ".join([interaction.guild.get_role(ids).mention for ids in self.data["manager_roles"]]))
                await interaction.message.edit(embed=embed)
                await interaction.client.payout_config.update(self.data)
                

        else:
            await interaction.edit_original_response(content="No role selected", view=None)
