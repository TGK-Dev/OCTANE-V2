import discord
from .selects import Channel_select, Role_select
from discord import Interaction

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
    
    @discord.ui.button(label="Clain Channel", style=discord.ButtonStyle.gray, emoji="<:channel:1017378607863181322>")
    async def claim_channel(self, interaction: discord.Interaction, button: discord.ui.Button):

        view = discord.ui.View()
        view.value = False
        view.select = Channel_select("select new claim channel", max_values=1, min_values=1, disabled=False, channel_types=[discord.ChannelType.text])
        view.add_item(view.select)

        await interaction.response.send_message(content="Select a new channel from the dropdown menu below", view=view, ephemeral=True)
        await view.wait()

        if view.value:
                
            self.data["pending_channel"] = view.select.values[0].id
            await view.select.interaction.response.edit_message(content="Suscessfully updated claim channel", view=None)
            embed = interaction.message.embeds[0]
            embed.set_field_at(1, name="Claim Channel", value=view.select.values[0].mention)
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


class Payout_clain(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="claim", style=discord.ButtonStyle.blurple, custom_id="payout:claim")
    async def payout_claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        loading_embed = discord.Embed(description="<a:loading:998834454292344842> | Processing claim...", color=discord.Color.yellow())
        await interaction.response.send_message(embed=loading_embed, ephemeral=True)

        data = await interaction.client.payout_queue.find(interaction.message.id)
        if not data: await interaction.edit_original_response(embed=discord.Embed(description="<:octane_no:1019957208466862120> | This payout has already been claimed or invalid", color=discord.Color.red()))

        if interaction.user.id != data['winner']:
            await interaction.edit_original_response(embed=discord.Embed(description="<:octane_no:1019957208466862120> | You are not the winner of this payout", color=discord.Color.red()))
            return
        
        await interaction.edit_original_response(embed=discord.Embed(description="<:octane_yes:1019957051721535618> | Sucessfully claimed payout, you will be paid in 24hrs", color=discord.Color.green()))
        data['claimed'] = True
        await interaction.client.payout_queue.update(data)

        payout_config = await interaction.client.payout_config.find(interaction.guild.id)
        queue_channel = interaction.guild.get_channel(payout_config['queue_channel'])

        embed = interaction.message.embeds[0]

        msg = await queue_channel.send(f"<@{data['winner']}> you will be paid out in the next 24hrs!\n> If not paid within the deadline claim from support chanel", embed=embed, view=Payout_Buttton())
        pending_data = data
        pending_data['_id'] = msg.id
        await interaction.client.payout_pending.insert(pending_data)
        await interaction.client.payout_queue.delete(interaction.message.id)
        button.label = "Claimed Successfully"
        button.style = discord.ButtonStyle.green
        button.disabled = True
        await interaction.message.edit(view=self)

    async def on_error(self, interaction: Interaction, error: Exception, item: discord.ui.Item):
        try:
            await interaction.response.send_message(f"Error: {error}", ephemeral=True)
        except:
            await interaction.edit_original_response(content=f"Error: {error}")

class Payout_Buttton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Payout", style=discord.ButtonStyle.green, custom_id="payout")
    async def payout(self, interaction: discord.Interaction, button: discord.ui.Button):
        loadin_embed = discord.Embed(description="<a:loading:998834454292344842> | Marking payout...", color=discord.Color.blue())
        await interaction.response.send_message(embed=loadin_embed, ephemeral=True)

        data = await interaction.client.payout_pending.find(interaction.message.id)
        if not data: await interaction.edit_original_response(embed=discord.Embed(description="<:dynoError:1000351802702692442> | Payout not found in Database", color=discord.Color.red()))

        embed = interaction.message.embeds[0]
        embed.remove_field(len(embed.fields)-1)
        embed.add_field(name="Payout Status", value="**<:nat_reply_cont:1011501118163013634> Done**")
        embed.title = "Successfull Payment!"
        embed.color = discord.Color.green()
        embed.add_field(name="Santioned By", value=f"**<:nat_reply_cont:1011501118163013634> {interaction.user.mention}**")
        button.disabled = True
        button.label = "Payout Successfully!"

        
        winner_channel = interaction.client.get_channel(data['channel'])
        winner_message = await winner_channel.fetch_message(data['winner_message_id'])
        
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label=f'Winner Message', url=f"{winner_message.jump_url}"))
        view.add_item(discord.ui.Button(label=f'Payout Queue Message', url=f"{interaction.message.jump_url}"))
        success_embed = discord.Embed(description="<:octane_yes:1019957051721535618> | Payout Marked Successfully!", color=discord.Color.green())
        await interaction.edit_original_response(embed=success_embed, view=view)
        await interaction.message.edit(view=self, embed=embed, content=None)
        await interaction.client.payout_pending.delete(data['_id'])
        
        is_more_payout_pending = await interaction.client.payout_pending.find_many_by_custom({'winner_message_id': data['winner_message_id']})
        if len(is_more_payout_pending) <= 0:
            loading_emoji = await interaction.client.emoji_server.fetch_emoji(998834454292344842)
            paid_emoji = await interaction.client.emoji_server.fetch_emoji(1052528036043558942)
            winner_channel = interaction.client.get_channel(data['channel'])
            try:
                winner_message = await winner_channel.fetch_message(data['winner_message_id'])
                await winner_message.remove_reaction(loading_emoji, interaction.client.user)
                await winner_message.add_reaction(paid_emoji)
            except Exception as e:
                pass

    async def on_error(self, interaction: Interaction, error: Exception, item: discord.ui.Item):
        try:
            await interaction.response.send_message(f"Error: {error}", ephemeral=True)
        except:
            await interaction.edit_original_response(content=f"Error: {error}")

    async def interaction_check(self, interaction: Interaction):
        config = await interaction.client.payout_config.find(interaction.guild.id)
        roles = [role.id for role in interaction.user.roles]
        if (set(roles) & set(config['manager_roles'])): return True
        else:
            embed = discord.Embed(title="Error", description="You don't have permission to use this button", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
