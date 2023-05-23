import asyncio
import discord
import re
import humanfriendly
from .selects import Channel_select, Role_select
from .modal import General_Modal
from discord import Interaction
from utils.converters import TimeConverter
from .buttons import Link_view
import datetime
from .buttons import Confirm

class Payout_Config_Edit(discord.ui.View):
    def __init__(self, data: dict, user: discord.Member,message: discord.Message=None, interaction: Interaction=None):
        self.data = data
        self.message = message
        self.user = user
        self.interaction = interaction
        super().__init__(timeout=120)
    
    async def on_timeout(self):
        for child in self.children: child.disabled = True
        await self.message.edit(view=self)
    
    async def on_error(self, error, item, interaction):
        try:
            await interaction.response.send_message(f"An error occured: {error}", ephemeral=True)
        except:
            await interaction.edit_original_response(f"An error occured: {error}")
    
    async def interaction_check(self, interaction: Interaction):
        if interaction.user.id == self.user.id:
            return True
        else:
            await interaction.response.send_message("you can't use this view", ephemeral=True)
            return False

    def update_embed(self, data:dict, interaction: Interaction):
        
        embed = discord.Embed(title="Payout Config", description="", color=0x2b2d31)
        embed.description += f"**Queue Channel:** {interaction.guild.get_channel(data['queue_channel']).mention if data['queue_channel'] else '`Not Set`'}\n"
        embed.description += f"**Pending Channel:** {interaction.guild.get_channel(data['pending_channel']).mention if data['pending_channel'] else '`Not Set`'}\n"
        embed.description += f"**Payout Channel:** {interaction.guild.get_channel(data['payout_channel']).mention if data['payout_channel'] else '`Not Set`'}\n"
        embed.description += f"**Log Channel:** {interaction.guild.get_channel(data['log_channel']).mention if data['log_channel'] else '`Not Set`'}\n"
        embed.description += f"**Manager Roles:** {', '.join([f'<@&{role}>' for role in data['manager_roles']]) if data['manager_roles'] else '`Not Set`'}\n"
        embed.description += f"**Event Manager Roles:** {', '.join([f'<@&{role}>' for role in data['event_manager_roles']]) if data['event_manager_roles'] else '`Not Set`'}\n"
        embed.description += f"**Default Claim Time:** {humanfriendly.format_timespan(data['default_claim_time'])}\n"

        return embed
    
    @discord.ui.button(label="Queue Channel", style=discord.ButtonStyle.gray, emoji="<:channel:1017378607863181322>", row=0)
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
            embed = self.update_embed(self.data, interaction)
            await interaction.client.payout_config.update(self.data)
            await interaction.message.edit(embed=embed)
        else:
            await interaction.edit_original_response(content="No channel selected", view=None)
    
    @discord.ui.button(label="Clain Channel", style=discord.ButtonStyle.gray, emoji="<:channel:1017378607863181322>", row=0)
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
            embed = self.update_embed(self.data, interaction)
            await interaction.client.payout_config.update(self.data)
            await interaction.message.edit(embed=embed)
        else:
            await interaction.edit_original_response(content="No channel selected", view=None)
    
    @discord.ui.button(label="Payout Channel", style=discord.ButtonStyle.gray, emoji="<:channel:1017378607863181322>", row=0)
    async def payout_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
            
            view = discord.ui.View()
            view.value = False
            view.select = Channel_select("Select new payout channel", max_values=1, min_values=1, disabled=False, channel_types=[discord.ChannelType.text])
            view.add_item(view.select)
    
            await interaction.response.send_message(view=view, ephemeral=True)
            await view.wait()
    
            if view.value:
                self.data["payout_channel"] = view.select.values[0].id
                await view.select.interaction.response.edit_message(content="Suscessfully updated payout channel", view=None)
                embed = self.update_embed(self.data, interaction)
                await interaction.client.payout_config.update(self.data)
                await interaction.message.edit(embed=embed)
            else:
                await interaction.edit_original_response(content="No channel selected", view=None)
            
    
    @discord.ui.button(label="Log Channel", style=discord.ButtonStyle.gray, emoji="<:channel:1017378607863181322>", row=1)
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
                embed = self.update_embed(self.data, interaction)
                await interaction.message.edit(embed=embed)
                await interaction.client.payout_config.update(self.data)
            else:
                await interaction.edit_original_response(content="No channel selected", view=None)
    
    @discord.ui.button(label="Manager Role", style=discord.ButtonStyle.gray, emoji="<:role_mention:1063755251632582656>", row=1)
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

                embed = self.update_embed(self.data, interaction)
                await interaction.message.edit(embed=embed)
                await interaction.client.payout_config.update(self.data)
        else:
            await interaction.edit_original_response(content="No role selected", view=None)
    
    @discord.ui.button(label="Event Managers", style=discord.ButtonStyle.gray, emoji="<:role_mention:1063755251632582656>", row=1)
    async def event_managers(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View()
        view.value = False
        view.select = Role_select("select new event manager role", max_values=10, min_values=1, disabled=False)
        view.add_item(view.select)

        await interaction.response.send_message(content="Select a new role from the dropdown menu below", view=view, ephemeral=True)
        await view.wait()

        if view.value:
                added = []
                removed = []
                for ids in view.select.values:
                    if ids.id not in self.data["event_manager_roles"]:
                        self.data["event_manager_roles"].append(ids.id)
                        added.append(ids.mention)
                    else:
                        self.data["event_manager_roles"].remove(ids.id)
                        removed.append(ids.mention)
                await view.select.interaction.response.edit_message(content=f"Suscessfully updated event manager roles\nAdded: {', '.join(added)}\nRemoved: {', '.join(removed)}", view=None)

                embed = self.update_embed(self.data, interaction)
                await interaction.message.edit(embed=embed)
                await interaction.client.payout_config.update(self.data)
        else:
            await interaction.edit_original_response(content="No role selected", view=None)

    @discord.ui.button(label="Claim Time", style=discord.ButtonStyle.gray, emoji="<:octane_claim_time:1071517327813775470>", row=2)
    async def claim_time(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = General_Modal("Claim Time Modal", interaction=interaction)
        modal.question = discord.ui.TextInput(label="Enter New Claim Time", placeholder="Enter New Claim Time exp: 1h45m", min_length=1, max_length=10)    
        modal.value = None
        modal.add_item(modal.question)
        await interaction.response.send_modal(modal)

        await modal.wait()
        if modal.value:
            time = await TimeConverter().convert(modal.interaction, modal.question.value)
            if time < 3600: await modal.interaction.response.send_message("Claim time must be at least 1 hour", ephemeral=True)
            self.data['default_claim_time'] = time
            await interaction.client.payout_config.update(self.data)
            embed = self.update_embed(self.data, modal.interaction)
            await modal.interaction.response.edit_message(embed=embed, view=self)

class Payout_claim(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Claim", style=discord.ButtonStyle.green, custom_id="payout:claim")
    async def payout_claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        loading_embed = discord.Embed(description="<a:loading:998834454292344842> | Processing claim...", color=discord.Color.yellow())
        await interaction.response.send_message(embed=loading_embed, ephemeral=True)

        data = await interaction.client.payout_queue.find(interaction.message.id)
        if not data: return await interaction.edit_original_response(embed=discord.Embed(description="<:octane_no:1019957208466862120> | This payout has already been claimed or invalid", color=discord.Color.red()))

        if interaction.user.id != data['winner']:
            await interaction.edit_original_response(embed=discord.Embed(description="<:octane_no:1019957208466862120> | You are not the winner of this payout", color=discord.Color.red()))
            return
        
        data['claimed'] = True
        await interaction.client.payout_queue.update(data)

        payout_config = await interaction.client.payout_config.find(interaction.guild.id)
        queue_channel = interaction.guild.get_channel(payout_config['queue_channel'])

        queue_embed = interaction.message.embeds[0]
        queue_embed.description = queue_embed.description.replace("`Pending`", "`Awaiting Payment`")
        queue_embed_description = queue_embed.description.split("\n")
        queue_embed_description.pop(5)
        queue_embed.description = "\n".join(queue_embed_description)

        current_embed = interaction.message.embeds[0]
        current_embed.description = current_embed.description.replace("`Pending`", "`Claimed`")
        current_embed_description = current_embed.description.split("\n")
        current_embed_description[5] = f"~~{current_embed_description[5]}~~"


        await interaction.edit_original_response(embed=discord.Embed(description="<:octane_yes:1019957051721535618> | Sucessfully claimed payout, you will be paid in 24hrs", color=interaction.client.default_color))

        msg = await queue_channel.send(embed=queue_embed, view=Payout_Buttton(), content=f"> Payouts will be done within 24h.\n> Else make ticket from <#785901543349551104>.\n> {interaction.user.mention}")
        pending_data = data
        pending_data['_id'] = msg.id
        delete_queue_data = {'_id': interaction.message.id,'channel': interaction.message.channel.id,'now': datetime.datetime.utcnow(),'delete_after': 1800, 'reason': 'payout_claim'}
        await interaction.client.payout_delete_queue.insert(delete_queue_data)
        await interaction.client.payout_pending.insert(pending_data)
        await interaction.client.payout_queue.delete(interaction.message.id)

        button.label = "Claimed Successfully"
        button.style = discord.ButtonStyle.gray
        button.emoji = "<a:nat_check:1010969401379536958>"
        button.disabled = True
        self.add_item(discord.ui.Button(label=f'Payout Queue Message', style=discord.ButtonStyle.url, disabled=False, url=msg.jump_url))

        await interaction.message.edit(embed=current_embed, view=self)
        interaction.client.dispatch("payout_claim", interaction.message, interaction.user)
        interaction.client.dispatch("payout_pending", msg)

    async def on_error(self, interaction: Interaction, error: Exception, item: discord.ui.Item):
        try:
            await interaction.response.send_message(f"Error: {error}", ephemeral=True)
        except:
            await interaction.edit_original_response(content=f"Error: {error}")

class Payout_Buttton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    async def get_command(self, winner: discord.Member, amount: str, item=None):
        if item ==  None:
            return f"/serverevents payout user:{winner.id} quantity:{amount}"
        else:
            return f"/serverevents payout user:{winner.id} quantity:{amount} item:{item}"

    @discord.ui.button(label="Payout", style=discord.ButtonStyle.gray, emoji="<a:nat_check:1010969401379536958>", custom_id="payout")
    async def payout(self, interaction: discord.Interaction, button: discord.ui.Button):
        loadin_embed = discord.Embed(description="<a:loading:998834454292344842> | Generating command...", color=interaction.client.default_color)
        await interaction.response.send_message(embed=loadin_embed, ephemeral=True)

        data = await interaction.client.payout_pending.find(interaction.message.id)
        config = await interaction.client.payout_config.find(interaction.guild.id)

        if not data:
            return await interaction.edit_original_response(embed=discord.Embed(description="<:octane_no:1019957208466862120> | This payout has already been claimed or invalid", color=discord.Color.red()))
        
        winner = interaction.guild.get_member(data['winner'])
        amount = data['prize']
        if 'item' in data.keys():
            item = data['item']
        else:
            item = None

        if config['payout_channel'] != None:
            payout_channel = interaction.guild.get_channel(config['payout_channel'])
            if not payout_channel:
                return await interaction.edit_original_response(embed=discord.Embed(description="<:octane_no:1019957208466862120> | Payout channel not found", color=discord.Color.red()))
            
            embed = discord.Embed(title="Auto Payout Command", description="")
            embed.description += f"**Winner:** {winner.mention}\n"
            embed.description += f"**Amount:** {amount}\n"
            if item:
                embed.description += f"**Item:** {item}\n"
            
            embed.add_field(name="Command", value=await self.get_command(winner, amount, item))
            embed.set_footer(text="This command will be deleted in 30 seconds")
            payout_cmd = await payout_channel.send(embed=embed, delete_after=60)

            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Jump", style=discord.ButtonStyle.url, url=payout_cmd.jump_url))
            await interaction.edit_original_response(embed=discord.Embed(description="<:octane_yes:1019957051721535618> | Sucessfully generated payout command", color=interaction.client.default_color), view=view)
            
            update_embed = interaction.message.embeds[0]
            new_description = update_embed.description
            update_embed.title = "Successfully Paid!"
            update_embed.description = ""
            new_description = new_description.replace("`Awaiting Payment`", "`Paid`")
            update_embed.description = new_description
            update_embed.description += f"\n**Santioned By:** {interaction.user.mention}"
            update_embed.description += f"\n**Possible Payout Location:** {payout_cmd.jump_url}"
            edit_view = discord.ui.View()
            edit_view.add_item(discord.ui.Button(label=f'Successfully Paid', style=discord.ButtonStyle.gray, disabled=True, emoji="<:paid:1071752278794575932>"))

            winner_channel = interaction.guild.get_channel(data['channel'])
            winner_message = await winner_channel.fetch_message(data['winner_message_id'])

            winner_view = discord.ui.View()
            winner_view.add_item(discord.ui.Button(label=f'Winner Message', url=f"{winner_message.jump_url}"))
            winner_view.add_item(discord.ui.Button(label=f'Payout Queue Message', url=f"{interaction.message.jump_url}"))
            success_embed = discord.Embed(description="<:octane_yes:1019957051721535618> | Payout Marked Successfully!", color=discord.Color.green())

            await interaction.edit_original_response(embed=success_embed)
            await interaction.message.edit(embed=update_embed, view=edit_view, content=None)
            
            interaction.client.dispatch("payout_paid", interaction.message, interaction.user, winner, data['prize'])
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

    
    # @discord.ui.button(label="Payout", style=discord.ButtonStyle.gray, emoji="<a:nat_check:1010969401379536958>", custom_id="payout")
    # async def payout(self, interaction: discord.Interaction, button: discord.ui.Button):
    #     loadin_embed = discord.Embed(description="<a:loading:998834454292344842> | Marking payout...", color=discord.Color.blue())
    #     await interaction.response.send_message(embed=loadin_embed, ephemeral=True)

    #     data = await interaction.client.payout_pending.find(interaction.message.id)
    #     if not data: await interaction.edit_original_response(embed=discord.Embed(description="<:dynoError:1000351802702692442> | Payout not found in Database", color=discord.Color.red()))

    #     embed = interaction.message.embeds[0]
    #     new_description = embed.description
    #     embed.title = "Successfully Paid!"
    #     embed.description = ""
    #     new_description = new_description.replace("`Awaiting Payment`", "`Paid`")
    #     embed.description = new_description
    #     embed.description += f"\n**Santioned By:** {interaction.user.mention}"
    #     edit_view = discord.ui.View()
    #     edit_view.add_item(discord.ui.Button(label=f'Successfully Paid', style=discord.ButtonStyle.gray, disabled=True, emoji="<:paid:1071752278794575932>"))

    #     winner_channel = interaction.client.get_channel(data['channel'])
    #     winner_message = await winner_channel.fetch_message(data['winner_message_id'])
        
    #     view = discord.ui.View()
    #     view.add_item(discord.ui.Button(label=f'Winner Message', url=f"{winner_message.jump_url}"))
    #     view.add_item(discord.ui.Button(label=f'Payout Queue Message', url=f"{interaction.message.jump_url}"))
    #     success_embed = discord.Embed(description="<:octane_yes:1019957051721535618> | Payout Marked Successfully!", color=discord.Color.green())
    #     await interaction.edit_original_response(embed=success_embed)
    #     await interaction.message.edit(view=edit_view, embed=embed, content=None)
    #     winner = interaction.guild.get_member(data['winner'])
    #     interaction.client.dispatch("payout_paid", interaction.message, interaction.user, winner, data['prize'])
    #     await interaction.client.payout_pending.delete(data['_id'])
        
    #     is_more_payout_pending = await interaction.client.payout_pending.find_many_by_custom({'winner_message_id': data['winner_message_id']})
    #     if len(is_more_payout_pending) <= 0:
    #         loading_emoji = await interaction.client.emoji_server.fetch_emoji(998834454292344842)
    #         paid_emoji = await interaction.client.emoji_server.fetch_emoji(1052528036043558942)
    #         winner_channel = interaction.client.get_channel(data['channel'])
    #         try:
    #             winner_message = await winner_channel.fetch_message(data['winner_message_id'])
    #             await winner_message.remove_reaction(loading_emoji, interaction.client.user)
    #             await winner_message.add_reaction(paid_emoji)
    #         except Exception as e:
    #             pass
    
    @discord.ui.button(label="Reject", style=discord.ButtonStyle.gray, emoji="<a:nat_cross:1010969491347357717>", custom_id="reject")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = Confirm(interaction.user, 30)
        await interaction.response.send_message("Are you sure you want to reject this payout?", view=view, ephemeral=True)
        await view.wait()
        if not view.value: return await interaction.delete_original_response()
        data = await interaction.client.payout_pending.find(interaction.message.id)
        if not data: return await view.interaction.response.edit_message(embed=discord.Embed(description="<:dynoError:1000351802702692442> | Payout not found in Database", color=discord.Color.red()))

        embed = interaction.message.embeds[0]
        embed.description = embed.description.replace("`Awaiting Payment`", "`Payout Rejected`")
        embed.title = "Payout Rejected"
        embed.description += f"\n**Rejected By:** {interaction.user.mention}"

        edit_view = discord.ui.View()
        edit_view.add_item(discord.ui.Button(label=f'Payout Denied', style=discord.ButtonStyle.gray, disabled=True, emoji="<a:nat_cross:1010969491347357717>"))

        winner_channel = interaction.client.get_channel(data['channel'])

        await view.interaction.response.edit_message(embed=discord.Embed(description="<:octane_yes:1019957051721535618> | Payout Rejected Successfully!", color=interaction.client.default_color), view=None)
        await interaction.message.edit(view=edit_view, embed=embed, content=None)
        await interaction.client.payout_pending.delete(data['_id'])

    # async def on_error(self, interaction: Interaction, error: Exception, item: discord.ui.Item):
    #     try:
    #         await interaction.response.send_message(f"Error: {error}", ephemeral=True)
    #     except:
    #         await interaction.edit_original_response(content=f"Error: {error}")

    async def interaction_check(self, interaction: Interaction):
        config = await interaction.client.payout_config.find(interaction.guild.id)
        roles = [role.id for role in interaction.user.roles]
        if (set(roles) & set(config['manager_roles'])): return True
        else:
            embed = discord.Embed(title="Error", description="You don't have permission to use this button", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
