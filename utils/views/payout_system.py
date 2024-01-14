import asyncio
import discord
import re
import humanfriendly
from .selects import Channel_select, Role_select
from .modal import General_Modal
from discord import Interaction, app_commands
from discord.ext import commands
from utils.converters import TimeConverter
from .buttons import Link_view
import datetime
from .buttons import Confirm

class ButtonCooldown(app_commands.CommandOnCooldown):
    def __init__(self, retry_after: float):
        self.retry_after = retry_after

    def key(interaction: discord.Interaction):
        return interaction.user

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
    
    @discord.ui.button(label="Claim Channel", style=discord.ButtonStyle.gray, emoji="<:channel:1017378607863181322>", row=0)
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
        self.cd = app_commands.Cooldown(1, 10)

    async def interaction_check(self, interaction: discord.Interaction):
        retry_after = self.cd.update_rate_limit()
        if retry_after:
            raise ButtonCooldown(retry_after)
        return True
    
    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        if isinstance(error, ButtonCooldown):
            seconds = int(error.retry_after)
            unit = 'second' if seconds == 1 else 'seconds'
            await interaction.response.send_message(f"You're on cooldown for {seconds} {unit}!", ephemeral=True)
        else:
            # call the original on_error, which prints the traceback to stderr
            await super().on_error(interaction, error, item)
    
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

        view = Payout_Buttton()
        view.remove_item(view.children[0])
        msg = await queue_channel.send(embed=queue_embed, view=view)
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
        self.children[1].disabled = True
        self.add_item(discord.ui.Button(label=f'Payout Queue Message', style=discord.ButtonStyle.url, disabled=False, url=msg.jump_url))

        await interaction.message.edit(embed=current_embed, view=self)
        interaction.client.dispatch("payout_claim", interaction.message, interaction.user)
        interaction.client.dispatch("payout_pending", msg)


    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, custom_id="payout:cancel")
    async def payout_cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        payout_data = await interaction.client.payout_queue.find(interaction.message.id)
        if payout_data['set_by'] != interaction.user.id:
            config = await interaction.client.payout_config.find(interaction.guild.id)
            user_roles = [role.id for role in interaction.user.roles]
            if (set(user_roles) & set(config['event_manager_roles'])):
                pass
            else:
                return await interaction.response.send_message("You are not allowed to use this button!", ephemeral=True)        
        else:
            modal = General_Modal("Reason for cancelling payout?", interaction)
            modal.reason = discord.ui.TextInput(label="Reason", placeholder="Reason for cancelling payout", min_length=3, max_length=100, required=True)
            modal.add_item(modal.reason)
            await interaction.response.send_modal(modal)

            await modal.wait()
            if modal.value:
                loading_embed = discord.Embed(description="<a:loading:998834454292344842> | Processing claim...", color=discord.Color.yellow())
                await modal.interaction.response.send_message(embed=loading_embed, ephemeral=True)

                embed = interaction.message.embeds[0]
                embed.title = "Payout Cancelled"
                embed.description = embed.description.replace("`Pending`", "`Cancelled`")
                embed.description += f"\n**Cancelled by:** {interaction.user.mention}\n**Reason:** {modal.reason.value}"

                temp_view = discord.ui.View()
                temp_view.add_item(discord.ui.Button(label="Payout Cancelled", style=discord.ButtonStyle.gray, emoji="<a:nat_cross:1010969491347357717>",disabled=True))
                await interaction.message.edit(embed=embed, view=temp_view, content=None)
                await interaction.client.payout_queue.delete(interaction.message.id)
                
                await modal.interaction.edit_original_response(embed=discord.Embed(description="Sucessfully cancelled payout", color=discord.Color.green()))

class Payout_Buttton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.cd = app_commands.Cooldown(5, 10)

    
    async def get_command(self, winner: discord.Member, amount: str, item=None):
        if item ==  None:
            return f"/serverevents payout user:{winner.id} quantity:{amount}"
        else:
            return f"/serverevents payout user:{winner.id} quantity:{amount} item:{item}"
    
    @discord.ui.button(label="Reject", style=discord.ButtonStyle.gray, emoji="<a:nat_cross:1010969491347357717>", custom_id="reject")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = Confirm(interaction.user, 30)
        await interaction.response.send_message("Are you sure you want to reject this payout?", view=view, ephemeral=False)
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
    
    @discord.ui.button(label="Manual Verification", style=discord.ButtonStyle.gray, emoji="<:caution:1122473257338151003>", custom_id="manual_verification", disabled=False)
    async def manual_verification(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = General_Modal(title="Manual Verification", interaction=interaction)
        view.msg = discord.ui.TextInput(label="Message Link", placeholder="Enter the message link of te confirmation message", max_length=100, required=True, style=discord.TextStyle.long)
        view.add_item(view.msg)

        await interaction.response.send_modal(view)
        await view.wait()
        if not view.value: return
        msg_link = view.msg.value
        await view.interaction.response.send_message("Verifying...", ephemeral=True)
        data = await interaction.client.payout_pending.find(interaction.message.id)
        try:
            msg_id = int(msg_link.split("/")[-1])
            msg_channel = int(msg_link.split("/")[-2])
            channel = interaction.guild.get_channel(msg_channel)
            message = await channel.fetch_message(msg_id)

            if message.author.id != 270904126974590976: raise Exception("Invalid Message Link")
            if len(message.embeds) <= 0: raise Exception("Invalid Message Link")

            embed = message.embeds[0]
            if not embed.description.startswith("Successfully paid"): raise Exception("Invalid Message Link")

            winner = message.guild.get_member(int(embed.description.split(" ")[2].replace("<", "").replace(">", "").replace("!", "").replace("@", ""))) 
            if not winner: raise Exception("Invalid Message Link")
            if winner.id != data['winner']: return await view.interaction.edit_original_response(content="The winner of the provided message is not the winner of this payout")

            items = re.findall(r"\*\*(.*?)\*\*", embed.description)[0]
            if "⏣" in items:
                items = int(items.replace("⏣", "").replace(",", ""))
                if items == data['prize']:
                    await view.interaction.edit_original_response(content="Verified Successfully")
                else:
                    return await view.interaction.edit_original_response(content="The prize of the provided message is not the prize of this payout")
            else:
                emojis = list(set(re.findall(":\w*:\d*", items)))
                for emoji in emojis :items = items.replace(emoji,"",100); items = items.replace("<>","",100);items = items.replace("<a>","",100);items = items.replace("  "," ",100)
                mathc = re.search(r"(\d+)x (.+)", items)
                item_found = mathc.group(2)
                quantity_found = int(mathc.group(1).replace(",","",100))
                if item_found == data['item'] and quantity_found == data['prize']:
                    await view.interaction.edit_original_response(content="Verified Successfully")
                else:
                    return await view.interaction.edit_original_response(content="The prize of the provided message is not the prize of this payout")
            
            payot_embed = interaction.message.embeds[0]
            payot_embed.description += f"\n**Payout Location:** {message.jump_url}"
            payot_embed.description = payot_embed.description.replace("`Initiated`", "`Successfuly Paid`")
            payot_embed.description = payot_embed.description.replace("`Awaiting Payment`", "`Successfuly Paid`")
            payot_embed.description += f"\n**Santioned By:** {interaction.user.mention}"
            payot_embed.title = "Successfully Paid"
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label=f"Paid at", style=discord.ButtonStyle.url, url=message.jump_url, emoji="<:tgk_link:1105189183523401828>"))
            await interaction.message.edit(embed=payot_embed, view=view)   
            await interaction.client.payout_pending.delete(data['_id'])             
        except Exception as e:
            print(e)
            return await view.interaction.edit_original_response(content="Invalid Message Link")

    async def on_error(self, interaction: Interaction, error: Exception, item: discord.ui.Item):
        if isinstance(error, ButtonCooldown):
            seconds = int(error.retry_after)
            unit = 'second' if seconds == 1 else 'seconds'
            return await interaction.response.send_message(f"You're on cooldown for {seconds} {unit}!", ephemeral=True)
        try:
            await interaction.response.send_message(f"Error: {error}", ephemeral=True)
        except Exception as e:
            print(e)
            await interaction.edit_original_response(content=f"Error: {error}")

    async def interaction_check(self, interaction: Interaction):
        config = await interaction.client.payout_config.find(interaction.guild.id)
        roles = [role.id for role in interaction.user.roles]
        if (set(roles) & set(config['manager_roles'])): 
            retry_after = self.cd.update_rate_limit()
            if retry_after:
                raise ButtonCooldown(retry_after)
            return True
        else:
            embed = discord.Embed(title="Error", description="You don't have permission to use this button", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False


