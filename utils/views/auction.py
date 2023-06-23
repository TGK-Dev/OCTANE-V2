import discord
from discord import Interaction
from discord.ui import View, Button, Select, button
from .selects import Role_select, Channel_select


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
        embed.description += f"**Payout Channel:** {interaction.guild.get_channel(auction_data['payout_channel']).mention if auction_data['payout_channel'] else '`None`'}\n"
        embed.description += f"**Manager Roles:** {', '.join([f'<@&{role}>' for role in auction_data['manager_roles']]) if len(auction_data['manager_roles']) > 0 else '`None`'}\n"
        return embed
    
    @button(label="Category", style=discord.ButtonStyle.gray, emoji="<:category:1068484752664973324>", row=0)
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
            await interaction.client.auction.config.update(self.data)
    
    @button(label="Request Channel", style=discord.ButtonStyle.gray, emoji="<:channel:1017378607863181322>", row=0)
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
            await interaction.client.auction.config.update(self.data)
    
    @button(label="Queue Channel", style=discord.ButtonStyle.gray, emoji="<:channel:1017378607863181322>", row=0)
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
            await interaction.client.auction.config.update(self.data)
    
    @button(label="Bid Channel", style=discord.ButtonStyle.gray, emoji="<:channel:1017378607863181322>", row=0)
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
            await interaction.client.auction.config.update(self.data)
    
    @button(label="Payment Channel", style=discord.ButtonStyle.gray, emoji="<:channel:1017378607863181322>", row=0)
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
            await interaction.message.edit(embed=embed, view=self)
    
    @button(label="Payout Channel", style=discord.ButtonStyle.gray, emoji="<:channel:1017378607863181322>", row=1)
    async def Payout_channel(self, interaction: Interaction, button: Button):
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
            self.data["payout_channel"] = view.select.values[0].id
            await interaction.delete_original_response()
            embed = await self.update_embed(interaction, self.data)
            await interaction.message.edit(embed=embed, view=self)
    
    @button(label="Log Channel", style=discord.ButtonStyle.gray, emoji="<:channel:1017378607863181322>", row=1)
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
    
    @button(label="Manager Roles", style=discord.ButtonStyle.gray, emoji="<:role:1017378607863181322>", row=1)
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
            await interaction.client.auction.config.update(self.data)
            embed = await self.update_embed(interaction, self.data)
            await interaction.message.edit(embed=embed, view=self)

    @button(label="Automatic Config", style=discord.ButtonStyle.gray, emoji="<:auto:1017378607863181322>", row=1)
    async def auto_config(self, interaction: Interaction, button: Button):
        await interaction.response.send_message("Please wait while I configure the auction system for you", ephemeral=True)
        overwrite = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True),
            interaction.user: discord.PermissionOverwrite(view_channel=True)
        }
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
        payout_channel = await interaction.guild.create_text_channel(name="Payouts", category=category, overwrites=overwrite)
        self.data["payout_channel"] = payout_channel.id
        logs_channel = await interaction.guild.create_text_channel(name="Logs", category=category, overwrites=overwrite)
        self.data["logs_channel"] = logs_channel.id
        await interaction.client.auction.config.update(self.data)
        embed = await self.update_embed(interaction, self.data)
        await interaction.edit_original_response(content="I have finished configuring the auction system for you, you still need to configure the manager roles")
        await interaction.message.edit(embed=embed, view=self)
