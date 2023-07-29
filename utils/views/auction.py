import discord
from discord import Interaction
from discord.ui import View, Button, Select, button
from .selects import Role_select, Channel_select
from .buttons import Confirm
from .modal import General_Modal
from utils.converters import DMCConverter_Ctx

class AuctionConfig(View):
    def __init__(self, member: discord.Member, data: dict, message: discord.Message=None):
        self.member = member
        self.data = data
        self.message = message
        super().__init__(timeout=None)
    
    async def interaction_check(self, interaction: Interaction):
        return interaction.user.id == self.member.id
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        try:
            await self.message.edit(view=self)
        except:
            pass
    
    async def update_embed(self, interaction: Interaction, auction_data: dict):
        embed = discord.Embed(title=f"{interaction.guild.name} Auction Config", color=interaction.client.default_color, description="")
        embed.description += f"**Category:** {interaction.guild.get_channel(auction_data['category']).mention if auction_data['category'] else '`None`'}\n"
        embed.description += f"**Request Channel:** {interaction.guild.get_channel(auction_data['request_channel']).mention if auction_data['request_channel'] else '`None`'}\n"
        embed.description += f"**Queue Channel:** {interaction.guild.get_channel(auction_data['queue_channel']).mention if auction_data['queue_channel'] else '`None`'}\n"
        embed.description += f"**Bid Channel:** {interaction.guild.get_channel(auction_data['bid_channel']).mention if auction_data['bid_channel'] else '`None`'}\n"
        embed.description += f"**Payment Channel:** {interaction.guild.get_channel(auction_data['payment_channel']).mention if auction_data['payment_channel'] else '`None`'}\n"
        embed.description += f"**Manager Roles:** {', '.join([f'<@&{role}>' for role in auction_data['manager_roles']]) if len(auction_data['manager_roles']) > 0 else '`None`'}\n"
        embed.description += f"**Ping Role:** {interaction.guild.get_role(auction_data['ping_role']).mention if auction_data['ping_role'] else '`None`'}\n"
        embed.description += f"**Minimum Worth:** {auction_data['minimum_worth']:,}\n" if auction_data['minimum_worth'] else '**Minimum Worth:** `None`'

        return embed
    
    @button(label="Category", style=discord.ButtonStyle.gray, emoji="<:tgk_channel:1073908465405268029>", row=0)
    async def category(self, interaction: Interaction, button: Button):
        embed = discord.Embed(description="Select a category for the ticket system to use", color=0x2b2d31)
        view = View()
        view.value = None
        view.select = Channel_select(placeholder="Select a category", min_values=1, max_values=1, channel_types=[discord.ChannelType.category])
        view.add_item(view.select)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True, delete_after=30)
        await view.wait()
        if view.value is None:
            await interaction.delete_original_response()
        else:
            self.data["category"] = view.select.values[0].id
            await interaction.delete_original_response()
            embed = await self.update_embed(interaction, self.data)
            await interaction.message.edit(embed=embed, view=self)
            await interaction.client.auction.update_config(interaction.guild.id, self.data)
    
    @button(label="Request Channel", style=discord.ButtonStyle.gray, emoji="<:tgk_channel:1073908465405268029>", row=0)
    async def Request_channel(self, interaction: Interaction, button: Button):
        embed = discord.Embed(description="Select a channel for the ticket system to use", color=0x2b2d31)
        view = View()
        view.value = None
        view.select = Channel_select(placeholder="Select a channel", min_values=1, max_values=1, channel_types=[discord.ChannelType.text])
        view.add_item(view.select)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True, delete_after=30)
        await view.wait()
        if view.value is None:
            await interaction.delete_original_response()
        else:
            self.data["request_channel"] = view.select.values[0].id
            await interaction.delete_original_response()
            embed = await self.update_embed(interaction, self.data)
            await interaction.message.edit(embed=embed, view=self)
            await interaction.client.auction.update_config(interaction.guild.id, self.data)
    
    @button(label="Queue Channel", style=discord.ButtonStyle.gray, emoji="<:tgk_channel:1073908465405268029>", row=0)
    async def Queue_channel(self, interaction: Interaction, button: Button):
        embed = discord.Embed(description="Select a channel for the ticket system to use", color=0x2b2d31)
        view = View()
        view.value = None
        view.select = Channel_select(placeholder="Select a channel", min_values=1, max_values=1, channel_types=[discord.ChannelType.text])
        view.add_item(view.select)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True, delete_after=30)
        await view.wait()
        if view.value is None:
            await interaction.delete_original_response()
        else:
            self.data["queue_channel"] = view.select.values[0].id
            await interaction.delete_original_response()
            embed = await self.update_embed(interaction, self.data)
            await interaction.message.edit(embed=embed, view=self)
            await interaction.client.auction.update_config(interaction.guild.id, self.data)
    
    @button(label="Bid Channel", style=discord.ButtonStyle.gray, emoji="<:tgk_channel:1073908465405268029>", row=1)
    async def Bid_channel(self, interaction: Interaction, button: Button):
        embed = discord.Embed(description="Select a channel for the ticket system to use", color=0x2b2d31)
        view = View()
        view.value = None
        view.select = Channel_select(placeholder="Select a channel", min_values=1, max_values=1, channel_types=[discord.ChannelType.text])
        view.add_item(view.select)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True, delete_after=30)
        await view.wait()
        if view.value is None:
            await interaction.delete_original_response()
        else:
            self.data["bid_channel"] = view.select.values[0].id
            await interaction.delete_original_response()
            embed = await self.update_embed(interaction, self.data)
            await interaction.message.edit(embed=embed, view=self)
            await interaction.client.auction.update_config(interaction.guild.id, self.data)
    
    @button(label="Payment Channel", style=discord.ButtonStyle.gray, emoji="<:tgk_channel:1073908465405268029>", row=1)
    async def Payment_channel(self, interaction: Interaction, button: Button):
        embed = discord.Embed(description="Select a channel for the ticket system to use", color=0x2b2d31)
        view = View()
        view.value = None
        view.select = Channel_select(placeholder="Select a channel", min_values=1, max_values=1, channel_types=[discord.ChannelType.text])
        view.add_item(view.select)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True, delete_after=30)
        await view.wait()
        if view.value is None:
            await interaction.delete_original_response()
        else:
            self.data["payment_channel"] = view.select.values[0].id
            await interaction.delete_original_response()
            embed = await self.update_embed(interaction, self.data)
            await interaction.client.auction.update_config(interaction.guild.id, self.data)
    
    @button(label="Log Channel", style=discord.ButtonStyle.gray, emoji="<:tgk_channel:1073908465405268029>", row=1)
    async def Log_channel(self, interaction: Interaction, button: Button):
        embed = discord.Embed(description="Select a channel for the ticket system to use", color=0x2b2d31)
        view = View()
        view.value = None
        view.select = Channel_select(placeholder="Select a channel", min_values=1, max_values=1, channel_types=[discord.ChannelType.text])
        view.add_item(view.select)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True, delete_after=30)
        await view.wait()
        if view.value is None:
            await interaction.delete_original_response()
        else:
            self.data["log_channel"] = view.select.values[0].id
            await interaction.delete_original_response()
            embed = await self.update_embed(interaction, self.data)
            await interaction.message.edit(embed=embed, view=self)
            await interaction.client.auction.update_config(interaction.guild.id, self.data)
    
    @button(label="Manager Roles", style=discord.ButtonStyle.gray, emoji="<:tgk_role:1073908306713780284>", row=2)
    async def manager_roles(self, interaction: Interaction, button: Button):
        view = View()
        view.value = None
        view.select = Role_select(placeholder="Please select the roles you want to be able to manage auctions", min_values=1, max_values=10)
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True, delete_after=30)
        await view.wait()
        if view.value is None:
            await interaction.delete_original_response()
        else:
            added = ""
            removed = ""
            for role in view.select.values:
                if role.id not in self.data["manager_roles"]:
                    self.data["manager_roles"].append(role.id)
                    added += f"{role.mention}\n"
                else:
                    self.data["manager_roles"].remove(role.id)
                    removed += f"{role.mention}\n"
            await view.select.interaction.response.edit_message(content=f"Added:\n{added}\nRemoved:\n{removed}", view=None)
            await interaction.client.auction.update_config(interaction.guild.id, self.data)
            embed = await self.update_embed(interaction, self.data)
            await interaction.message.edit(embed=embed, view=self)
    
    @button(label="Ping Role", style=discord.ButtonStyle.gray, emoji="<:tgk_role:1073908306713780284>", row=2)
    async def ping_role(self, interaction: Interaction, button: Button):
        view = View()
        view.value = None
        view.select = Role_select(placeholder="Please select the role you want to be pinged when an auction starts", min_values=1, max_values=1)
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True, delete_after=30)
        await view.wait()
        if view.value is None:
            await interaction.delete_original_response()
        else:
            self.data["ping_role"] = view.select.values[0].id
            await interaction.delete_original_response()
            embed = await self.update_embed(interaction, self.data)
            await interaction.message.edit(embed=embed, view=self)
        await interaction.client.auction.update_config(interaction.guild.id, self.data)

    @button(label="Mini Worth", style=discord.ButtonStyle.gray, emoji="<:tgk_bank:1073920882130558987>", row=2)
    async def mini_worth(self, interaction: Interaction, button: Button):
        modal = General_Modal(title="Auction Mini Worth", interaction=interaction)
        modal.worth = discord.ui.TextInput(label="Please enter the minimum worth for an auction", required=True)
        modal.worth.default = str(self.data["minimum_worth"]) if self.data["minimum_worth"] else None
        modal.add_item(modal.worth)
        await interaction.response.send_modal(modal)
        await modal.wait()
        if modal.value is None:
            return
        else:
            ammount = await DMCConverter_Ctx().convert(interaction, modal.worth.value)
            if not isinstance(ammount, int):
                await modal.interaction.response.send_message("Please enter a valid number", ephemeral=True)
                return
            self.data["minimum_worth"] = ammount
            await modal.interaction.response.edit_message(embed=await self.update_embed(interaction, self.data), view=self)
        await interaction.client.auction.update_config(interaction.guild.id, self.data)

    @button(label="Automatic Config", style=discord.ButtonStyle.gray, emoji="<:tgk_create:1107262030399930428>", row=3)
    async def auto_config(self, interaction: Interaction, button: Button):
        await interaction.response.send_message("Please wait while I configure the auction system for you", ephemeral=True)
        overwrite = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True),
            interaction.user: discord.PermissionOverwrite(view_channel=True)
        }
        if any([self.data["category"], self.data["request_channel"], self.data["queue_channel"], self.data["bid_channel"], self.data["payment_channel"], self.data["log_channel"]]):
            view = Confirm(interaction.user, 30)
            await interaction.edit_original_response(content="You already have a setup few channels, are you sure you want to continue?", view=view)
            view.message = await interaction.original_response()
            await view.wait()
            if view.value == False or None:
                await interaction.response.edit_message(content="Action cancelled", view=None, delete_after=10)
                return
            elif view.value:
                await view.interaction.response.edit_message(content="Please wait while I configure the auction system for you", view=None)

        category = await interaction.guild.create_category("Auctions", overwrites=overwrite)
        await interaction.guild.create_text_channel(name="Rules", category=category, overwrites=overwrite)
        self.data["category"] = category.id
        request_channel = await interaction.guild.create_text_channel(name="Requests", category=category, overwrites=overwrite)
        self.data["request_channel"] = request_channel.id
        queue_channel = await interaction.guild.create_text_channel(name="Queue", category=category, overwrites=overwrite)  
        self.data["queue_channel"] = queue_channel.id
        bid_channel = await interaction.guild.create_text_channel(name="Bids", category=category, overwrites=overwrite)
        self.data["bid_channel"] = bid_channel.id
        payment_channel = await interaction.guild.create_text_channel(name="Payments", category=category, overwrites=overwrite)
        self.data["payment_channel"] = payment_channel.id
        logs_channel = await interaction.guild.create_text_channel(name="Logs", category=category, overwrites=overwrite)
        self.data["logs_channel"] = logs_channel.id

        await interaction.client.auction.update_config(interaction.guild.id, self.data)
        embed = await self.update_embed(interaction, self.data)
        await interaction.edit_original_response(content="I have finished configuring the auction system for you, you still need to configure the manager roles")
        await interaction.message.edit(embed=embed, view=self)
