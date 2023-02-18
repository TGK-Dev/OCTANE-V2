import discord
from discord import Interaction, SelectOption
from discord.ui import View, Button, button, TextInput, Item
from .selects import Role_select, Select_General, Channel_select
from .modal import General_Modal

class LevelingConfig(View):
    def __init__(self, user: discord.Member, data: dict, message: discord.Message=None):
        self.user = user
        self.message = message
        self.data = data
        super().__init__(timeout=120)
    
    async def update_embed(self, interaction: Interaction, data):
        channel_multipliers = ""
        role_multipliers = ""
        for channel, multiplier in data['multiplier']['channels'].items(): channel_multipliers += f"<#{channel}>: `{multiplier}`\n"
        for role, multiplier in data['multiplier']['roles'].items(): role_multipliers += f"<@&{role}>: `{multiplier}`\n"

        embed = discord.Embed(title=f"{interaction.guild.name} Leveling Config", description="", color=interaction.client.default_color)
        embed.description += f"Global Multiplier: `{data['multiplier']['global']}`\n"
        embed.description += f"Cooldown: `{data['cooldown'] if data['cooldown'] else 'None'}`\n"
        embed.description += f"Clear On Leave: `{'On' if data['clear_on_leave'] else 'Off'}`\n"
        embed.description += f"Blacklisted Channels: {', '.join([f'<#{channel}>' for channel in data['blacklist']['channels']]) if data['blacklist']['channels'] else '`None`'}\n"
        embed.description += f"Blacklisted Roles: {', '.join([f'<@&{role}>' for role in data['blacklist']['roles']]) if data['blacklist']['roles'] else '`None`'}\n"                

        return embed

    async def interaction_check(self, interaction: Interaction):
        if interaction.user.id == self.user.id:
            return True
        else:
            await interaction.response.send_message(content="You don't have permission to use this!", ephemeral=True)
            return False
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view=self)
    
    async def on_error(self, error, item, interaction):
        try:
            await interaction.response.send_message(content=f"An error occured: {error}", ephemeral=True)
        except:
            await interaction.followup.send(content=f"An error occured: {error}", ephemeral=True)

    @button(label="Global Multiplier", style=discord.ButtonStyle.gray, emoji="<:tgk_add:1073902485959352362>", row=0)
    async def global_multiplier(self, interaction: Interaction, button: Button):
        view = View()
        view.value = False
        options = [SelectOption(label="1x", value="1"), SelectOption(label="2x", value="2"), SelectOption(label="3x", value="3"), SelectOption(label="4x", value="4"), SelectOption(label="5x", value="5"), SelectOption(label="6x", value="6"), SelectOption(label="7x", value="7"), SelectOption(label="8x", value="8"), SelectOption(label="9x", value="9"), SelectOption(label="10x", value="10")]
        view.select = Select_General(options=options, placeholder="Select the multiplier you want to set",min_values=1, max_values=1)
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()

        if view.value:
            self.data['multiplier']['global'] = int(view.select.values[0])
            await view.select.interaction.response.edit_message(content="Global multiplier set!", embed=None, view=None)
            await view.select.interaction.delete_original_response()
            await self.message.edit(embed=await self.update_embed(interaction, self.data))
            await interaction.client.level_config.update(interaction.guild.id, self.data)
            interaction.client.level_config_cache[interaction.guild.id] = self.data
    
    @button(label="Clear On Leave", style=discord.ButtonStyle.gray, emoji="<:tgk_removePerson:1073899271197298738>", row=0)
    async def clear_on_leave(self, interaction: Interaction, button: Button):
        if self.data['clear_on_leave']:
            self.data['clear_on_leave'] = False
            await interaction.response.send_message(content="Clear on leave has been disabled!", ephemeral=True, delete_after=5)
            await self.message.edit(embed=await self.update_embed(interaction, self.data))
        else:
            self.data['clear_on_leave'] = True
            await interaction.response.send_message(content="Clear on leave has been enabled!", ephemeral=True, delete_after=5)
            await self.message.edit(embed=await self.update_embed(interaction, self.data))
        await interaction.client.level_config.update(interaction.guild.id, self.data)
        interaction.client.level_config_cache[interaction.guild.id] = self.data

    @button(label="Blacklist Channels", style=discord.ButtonStyle.gray, emoji="<:tgk_channel:1073908465405268029>", row=1)
    async def blacklist_channels(self, interaction: Interaction, button: Button):
        view = View()
        view.value = False
        view.select = Channel_select(placeholder="Select the channels you want to blacklist", min_values=1, max_values=10, channel_types=[discord.ChannelType.text])
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()
        
        if view.value:
            add_channels = ""
            remove_channels = ""
            for channel in view.select.values:
                if channel.id not in self.data['blacklist']['channels']:
                    self.data['blacklist']['channels'].append(channel.id)
                    add_channels += f"<#{channel.id}> "
                else:
                    self.data['blacklist']['channels'].remove(channel.id)
                    remove_channels += f"<#{channel.id}> "

            await view.select.interaction.response.edit_message(content=f"Blacklisted channels: {add_channels if add_channels else 'None'}\nUnblacklisted channels: {remove_channels if remove_channels else 'None'}", embed=None, view=None)
            await self.message.edit(embed=await self.update_embed(interaction, self.data))
            await interaction.client.level_config.update(interaction.guild.id, self.data)
            interaction.client.level_config_cache[interaction.guild.id] = self.data
            await view.select.interaction.delete_original_response()

    @button(label="Blacklist Roles", style=discord.ButtonStyle.gray, emoji="<:tgk_role:1073908306713780284>", row=1)
    async def blacklist_roles(self, interaction: Interaction, button: Button):
        view = View()
        view.value = False
        view.select = Role_select(placeholder="Select the roles you want to blacklist",min_values=1, max_values=10)
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()
        
        if view.value:

            add_roles = ""
            remove_roles = ""
            for role in view.select.values:
                if role.id not in self.data['blacklist']['roles']:
                    self.data['blacklist']['roles'].append(role.id)
                    add_roles += f"<@&{role.id}> "
                else:
                    self.data['blacklist']['roles'].remove(role.id)
                    remove_roles += f"<@&{role.id}> "

            await view.select.interaction.response.edit_message(content=f"Blacklisted roles: {add_roles if add_roles else 'None'}\nUnblacklisted roles: {remove_roles if remove_roles else 'None'}", embed=None, view=None)
            await self.message.edit(embed=await self.update_embed(interaction, self.data))
            await interaction.client.level_config.update(interaction.guild.id, self.data)
            interaction.client.level_config_cache[interaction.guild.id] = self.data
            await view.select.interaction.delete_original_response()