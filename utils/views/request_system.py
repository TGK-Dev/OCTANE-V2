import discord
import datetime
from discord import Interaction, SelectOption, TextStyle
from discord.ui import View, Button, button, TextInput, Item
from .selects import Role_select, Select_General, Channel_select, User_Select
from .modal import General_Modal
from .buttons import Confirm
from utils.converters import DMCConverter_Ctx


class Config(View):
    def __init__(self, member: discord.Member, data: dict, message: discord.Message=None):
        self.member = member
        self.data = data
        self.message = message
        super().__init__(timeout=120)
    
    async def on_timeout(self):
        try:
            for child in self.children: child.disabled = True
            await self.message.edit(view=self)
        except discord.HTTPException:
            pass
    
    async def interaction_check(self, interaction: Interaction):
        if interaction.user.id == self.member.id:
            return True
        await interaction.response.send_message("Only the person who opened this config can use it", ephemeral=True)
        return False
    
    async def on_error(self, interaction: Interaction, error, item):
        try:
            await interaction.response.send_message(f"Error: {error}", ephemeral=True)
        except discord.InteractionResponded:
            await interaction.followup.send(f"Error: {error}", ephemeral=True)
    
    async def update_embed(self, interaction: discord.Interaction, data: dict):
        embed = discord.Embed(title="Event Request System", color=interaction.client.default_color, description="")
        embed.description += f"**Manager Roles:** {', '.join([f'<@&{role}>' for role in data['manager_roles']]) if data['manager_roles'] else 'None'}\n"
        embed.description += f"**Request Channel:** {interaction.guild.get_channel(data['request_channel']).mention if data['request_channel'] else 'None'}\n"
        embed.description += f"**Request Queue:** {interaction.guild.get_channel(data['request_queue']).mention if data['request_queue'] else 'None'}\n"
        embed.description += f"**Events:** {', '.join([f'`{event}`' for event in data['events'].keys()]) if data['events'] else 'None'}\n"

        if self.message:
            await self.message.edit(embed=embed)

    @button(label="Manager Roles", style=discord.ButtonStyle.gray, emoji="<:tgk_role:1073908306713780284>")
    async def _manager_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = View()
        view.value = None
        view.select = Role_select(placeholder="Select roles your want too add/remove", min_values=1, max_values=10)
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True)

        await view.wait()
        if not view.value:
            await interaction.delete_original_response()
        
        roles = view.select.values
        added = ""
        removed = ""
        
        for role in roles:
            if role in self.data["manager_roles"]:
                self.data["manager_roles"].remove(role.id)
                removed += f"{role.mention}"
            else:
                self.data["manager_roles"].append(role.id)
                added += f"{role.mention}"
        
        await view.select.interaction.response.edit_message(content=f"Added: {added}\nRemoved: {removed}", view=None)
        await self.update_embed(interaction, self.data)
        await interaction.client.events.update_config(self.data)
    
    @button(label="Channels", style=discord.ButtonStyle.gray, emoji="<:tgk_channel:1073908465405268029>")
    async def _channels(self, interaction: discord.Interaction, button: discord.ui.Button):
        view =  View()
        view.value = None
        view.select =  Select_General(placeholder="Select which channel settings you want to edit", max_values=1
                        ,options=[SelectOption(label="Request Channel", value="request_channel", description="The channel where members can request events", emoji="<:tgk_bid:1114854528018284595>"),SelectOption(label="Request Queue", value="request_queue", description="The channel where verified requests are sent", emoji="<:tgk_logging:1107652646887759973>")])
    
        view.add_item(view.select)
        await interaction.response.send_message(view=view, ephemeral=True)

        await view.wait()
        if not view.value:
            await interaction.delete_original_response()

        operation = view.select.values[0]

        channel_view = View()
        channel_view.value = None
        channel_view.select = Channel_select(placeholder="Select a channel which you want to set", max_values=1, min_values=1,channel_types=[discord.ChannelType.text])
        channel_view.add_item(channel_view.select)

        await view.select.interaction.response.edit_message(view=channel_view)
        await channel_view.wait()
        if not channel_view.value:
            await interaction.delete_original_response()

        channel = channel_view.select.values[0]
        if operation == "request_channel":
            self.data["request_channel"] = channel.id
        elif operation == "request_queue":
            self.data["request_queue"] = channel.id
        elif operation == "event_channel":
            self.data["event_channel"] = channel.id

        operation = operation.replace("_", " ").title()
        await channel_view.select.interaction.response.edit_message(content=f"Set {operation} to {channel.mention}", view=None)
        await self.update_embed(interaction, self.data)
        await interaction.client.events.update_config(self.data)

    @button(label="Events", style=discord.ButtonStyle.gray, emoji="<:tgk_announce:1123919566427406437>")
    async def _events(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = View()
        view.value = None
        view.select = Select_General(placeholder="Select which event settings you want to edit", max_values=1
                        ,options=[SelectOption(label="Add Event", value="add_event", description="Add an event", emoji="<:tgk_add:1073902485959352362>"),SelectOption(label="Remove Event", value="remove_event", description="Remove an event", emoji="<:tgk_delete:1113517803203461222>")])
        view.add_item(view.select)
        await interaction.response.send_message(view=view, ephemeral=True)

        await view.wait()
        if not view.value:
            await interaction.delete_original_response()

        operation = view.select.values[0]
        if operation == "add_event":
            modal = General_Modal(title="Event Creation", interaction=interaction)
            modal.name = TextInput(label="Event Name",placeholder="Event Name", min_length=1, max_length=100, style=TextStyle.short, required=True)
            modal.req_dono = TextInput(label="Minimum Dono",placeholder="Minimum Dono Required", min_length=1, max_length=100, style=TextStyle.short, required=True)
            modal.add_item(modal.name)
            modal.add_item(modal.req_dono)
            await view.select.interaction.response.send_modal(modal)
            await modal.wait()

            if modal.value == False:
                await interaction.delete_original_response()

            name = modal.name.value
            req_dono = await DMCConverter_Ctx().convert(modal.interaction, modal.req_dono.value)
            embed = discord.Embed(description="Event Name: {}\nRequired Dono: {}".format(name, req_dono), color=interaction.client.default_color)
            confrim = Confirm(interaction.user, 30)
            await modal.interaction.response.edit_message(embed=embed, view=confrim)
            confrim.message = await modal.interaction.original_response()
            await confrim.wait()
            if not confrim.value:
                await interaction.delete_original_response()
            
            self.data["events"][name] = {"name": name, "min_amount": req_dono}
            await self.update_embed(interaction, self.data)
            await confrim.interaction.response.edit_message(content="Event Created", view=None)
            await confrim.interaction.client.events.update_config(self.data)
            await interaction.delete_original_response()



class Event_view(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    async def on_interaction(self, interaction: Interaction):
        guild_config = await interaction.client.events.get_config(interaction.guild.id)
        if not guild_config:
            await interaction.response.send_message("Event system is not setup", ephemeral=True)
            return
        user_roles = [role.id for role in interaction.user.roles]
        if not (set(user_roles) & set(guild_config['manager_roles'])):
            await interaction.response.send_message("You are not allowed to use this command!", ephemeral=True)
            return False
        else:
            return True
    
    async def on_error(self, interaction: Interaction, error, item):
        try:
            await interaction.response.send_message(f"Error: {error}", ephemeral=True)
        except discord.InteractionResponded:
            await interaction.followup.send(f"Error: {error}", ephemeral=True)


    @button(label="Hosted", style=discord.ButtonStyle.gray, emoji="<:tgk_announce:1123919566427406437>", custom_id="EVENT:HOSTED")
    async def _hosted(self, interaction: Interaction, button: discord.ui.Button):
        modal = General_Modal(title="Event Hosting", interaction=interaction)
        modal_link = TextInput(label="Event Link",placeholder="Event Thread Link", max_length=1000, style=TextStyle.long, required=True)
        modal.add_item(modal_link)
        await modal.interaction.response.send_modal(modal)
        await modal.wait()
        if not modal.value:
            return
        link = modal_link.value
        embed = interaction.message.embeds[0]
        embed.description.replace("**Status:** Pending", "**Status:** Hosted")
        view = View()
        view.add_item(Button(label="Event Hosted At", url=link, style=discord.ButtonStyle.link, emoji="<:tgk_link:1105189183523401828>"))
        await interaction.message.edit(embed=embed, view=view)
        await interaction.client.events.delete({"_id": interaction.message.id, "guild_id": interaction.guild.id})

    
    


            





        


        
    
    
