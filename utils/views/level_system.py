import discord
import humanfriendly
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
        if data['enabled']:
            self.children[0].emoji = "<:toggle_on:1123932825956134912>"
        else:
            self.children[0].emoji = "<:toggle_off:1123932890993020928>"
    
    async def update_embed(self, interaction: Interaction, leveling_config):
        embed = discord.Embed(title="Leveling Config", color=interaction.client.default_color, description="")
        embed.description += f"**Leveling:** {leveling_config['enabled']}\n"
        embed.description += f"**Clear On Leave:** {leveling_config['clear_on_leave']}\n"
        embed.description += f"**Announcement Channel:** {interaction.guild.get_channel(leveling_config['announcement_channel']).mention if leveling_config['announcement_channel'] else '`None`'}\n"
        embed.description += f"**Global Multiplier:** `{leveling_config['global_multiplier']}`\n"
        embed.description += f"**Global Cooldown:** `{humanfriendly.format_timespan(leveling_config['cooldown'])}`\n"
        embed.description += f"**Multiplier Roles:**\n"
        for role, multi in leveling_config['multipliers']['roles'].items():
            embed.description += f"> `{multi}`: <:tgk_blank:1072224743266193459> <@&{role}> \n"
        
        embed.description += f"**Multiplier Channels:**\n"
        for channel, multi in leveling_config['multipliers']['channels'].items():
            embed.description += f"> `{multi}`: <:tgk_blank:1072224743266193459> <#{channel}> \n"
        
        rewards_roles = leveling_config['rewards']
        rewards_roles = sorted(rewards_roles.items(), key=lambda x: int(x[0]))
        embed.description += f"**Rewards:**\n"
        for level, role in rewards_roles:
            embed.description += f"> `{level}` : <:tgk_blank:1072224743266193459> <@&{role}>\n"

        embed.description += f"**Blacklist:**\n> Roles: {','.join([f'<@&{role}>' for role in leveling_config['blacklist']['roles']]) if leveling_config['blacklist']['roles'] else '`None`'}\n> Channels: {','.join([f'<#{channel}>' for channel in leveling_config['blacklist']['channels']]) if leveling_config['blacklist']['channels'] else '`None`'}\n"

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
    
    async def on_error(self, error, interaction):
        try:
            await interaction.response.send_message(content=f"An error occured: {error}", ephemeral=True)
        except:
            await interaction.followup.send(content=f"An error occured: {error}", ephemeral=True)
        
    @button(label="Toggle Leveling", style=discord.ButtonStyle.gray, emoji="<:tgk_toggle:1073899271197298738>", row=0)
    async def toggle_leveling(self, interaction: Interaction, button: Button):
        self.data['enabled']
        if self.data['enabled']:
            self.data['enabled'] = False
            button.emoji = "<:toggle_off:1123932890993020928>"
            await interaction.response.edit_message(embed=await self.update_embed(interaction, self.data), view=self)
        else:
            self.data['enabled'] = True
            button.emoji = "<:toggle_on:1123932825956134912>"
            await interaction.response.edit_message(embed=await self.update_embed(interaction, self.data), view=self)
        
        await interaction.client.level.update_config(interaction.guild, self.data)


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
            self.data['global_multiplier'] = int(view.select.values[0])
            await view.select.interaction.response.edit_message(content="Global multiplier set!", embed=None, view=None)
            await view.select.interaction.delete_original_response()
            await self.message.edit(embed=await self.update_embed(interaction, self.data))
            await interaction.client.level.update_config(interaction.guild, self.data)
    
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
        await interaction.client.level.update_config(interaction.guild, self.data)
    
    @button(label="Announcement Channel", style=discord.ButtonStyle.gray, emoji="<:tgk_announce:1123919566427406437>", row=1)
    async def announcement_channel(self, interaction: Interaction, button: Button):
        view = View()
        view.value = False
        view.select = Channel_select(placeholder="Select the channel you want to set", min_values=1, max_values=1, channel_types=[discord.ChannelType.text])
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()

        if view.value:
            if view.select.values[0].id == self.data['announcement_channel']:
                self.data['announcement_channel'] = None
                await view.select.interaction.response.edit_message(content="Announcement channel has been disabled!")
            else:
                self.data['announcement_channel'] = view.select.values[0].id
                await view.select.interaction.response.edit_message(content=f"Announcement channel has been set to <#{view.select.values[0].id}>!")
            await view.select.interaction.delete_original_response()
            await self.message.edit(embed=await self.update_embed(interaction, self.data))
            await interaction.client.level.update_config(interaction.guild, self.data)   

    @button(label="Multipliers Role", style=discord.ButtonStyle.gray, emoji="<:tgk_role:1073908306713780284>", row=1)
    async def multipliers_role(self, interaction: Interaction, button: Button):
        view = View()
        view.value = None
        view.select = Role_select(placeholder="Select the role you want to set multiplier for", min_values=1, max_values=1)
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()
        if not view.value: return await interaction.delete_original_message()
            
        muilt_role = view.select.values[0]
        multi_view = View()
        multi_view.value = None
        multi_view.select = Select_General(view.select.interaction, options=[SelectOption(label="1x", value="1"), SelectOption(label="2x", value="2"), SelectOption(label="3x", value="3"), SelectOption(label="4x", value="4"), SelectOption(label="5x", value="5"), SelectOption(label="6x", value="6"), SelectOption(label="7x", value="7"), SelectOption(label="8x", value="8"), SelectOption(label="9x", value="9"), SelectOption(label="10x", value="10")], placeholder="Select the multiplier you want to set",min_values=1, max_values=1)
        multi_view.add_item(multi_view.select)
        await view.select.interaction.response.edit_message(view=multi_view)
        await multi_view.wait()
        if not multi_view.value: return await interaction.delete_original_message()

        if multi_view.select.values[0] == "0":
            try:
                del self.data['multipliers']['roles'][str(view.select.values[0].id)]
            except KeyError:
                pass
            await multi_view.select.interaction.response.edit_message(content=f"Multiplier for {muilt_role.mention} has been removed!", embed=None, view=None)
        else:
            self.data['multipliers']['roles'][str(view.select.values[0].id)] = int(multi_view.select.values[0])
            await multi_view.select.interaction.response.edit_message(content=f"Multiplier for {muilt_role.mention} has been set to {multi_view.select.values[0]}x!", embed=None, view=None)

        await multi_view.select.interaction.delete_original_response()
        await interaction.client.level.update_config(interaction.guild, self.data)
        await self.message.edit(embed=await self.update_embed(interaction, self.data))
            
    @button(label="Multipliers Channels", style=discord.ButtonStyle.gray, emoji="<:tgk_channel:1073908465405268029>", row=1)
    async def multipliers_channels(self, interaction: Interaction, button: Button):
        view = View()
        view.value = False
        view.select = Channel_select(placeholder="Select the channels you want to set multiplier for", min_values=1, max_values=1, channel_types=[discord.ChannelType.text])
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()
        if not view.value: return await interaction.delete_original_message()
        
        multi_view = View()
        multi_view.value = None
        multi_view.select = Select_General(view.select.interaction, options=[SelectOption(label="1x", value="1"), SelectOption(label="2x", value="2"), SelectOption(label="3x", value="3"), SelectOption(label="4x", value="4"), SelectOption(label="5x", value="5"), SelectOption(label="6x", value="6"), SelectOption(label="7x", value="7"), SelectOption(label="8x", value="8"), SelectOption(label="9x", value="9"), SelectOption(label="10x", value="10")], placeholder="Select the multiplier you want to set",min_values=1, max_values=1)
        multi_view.add_item(multi_view.select)
        await view.select.interaction.response.edit_message(view=multi_view)
        await multi_view.wait()

        if not multi_view.value: return await interaction.delete_original_message()
                
        if multi_view.select.values[0] == "0":
            try:
                del self.data['multipliers']['channels'][str(view.select.values[0].id)]
            except KeyError:
                pass
            await multi_view.select.interaction.response.edit_message(content=f"Multiplier for <#{view.select.values[0].id}> has been removed!", embed=None, view=None)
        else:
            self.data['multipliers']['channels'][str(view.select.values[0].id)] = int(multi_view.select.values[0])
            await multi_view.select.interaction.response.edit_message(content=f"Multiplier for <#{view.select.values[0].id}> has been set to {multi_view.select.values[0]}x!", embed=None, view=None)

        await multi_view.select.interaction.delete_original_response()
        await interaction.client.level.update_config(interaction.guild, self.data)
        await self.message.edit(embed=await self.update_embed(interaction, self.data))

    @button(label="Blacklist Channels", style=discord.ButtonStyle.gray, emoji="<:tgk_channel:1073908465405268029>", row=2)
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
            await interaction.client.level.update_config(interaction.guild, self.data)
            await view.select.interaction.delete_original_response()

    @button(label="Blacklist Roles", style=discord.ButtonStyle.gray, emoji="<:tgk_role:1073908306713780284>", row=2)
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
            await interaction.client.level.update_config(interaction.guild, self.data)
            await view.select.interaction.delete_original_response()
    
    @button(label="Weekly Activity", style=discord.ButtonStyle.gray, emoji="<a:nat_message:1063077628036272158>", row=3)
    async def weekly_activity(self, interaction: Interaction, button: Button):
        view = General_Modal()
        view.value = False
        view.req = TextInput(label="Weekly Activity Requirement", placeholder="Enter the weekly activity requirement Enter (0) to disable", min_length=1, max_length=4)
        view.add_item(view.req)
        await interaction.response.send_modal(view)
        await view.wait()

        if not view.value: return
        if view.req.value == "0":
            self.data['weekly']['required_messages'] = 0
            await view.interaction.response.send_message(content="Weekly activity has been disabled!", embed=None, view=None)
        else:
            try:
                self.data['weekly']['required_messages'] = int(view.req.value)
            except ValueError:
                return await view.interaction.response.send_message(content="Invalid value entered!", embed=None, view=None)
            await view.interaction.response.send_message(content=f"Weekly activity requirement has been set to {view.req.value} messages!\nNote: You can't this info in config embed", embed=None, view=None)
        await interaction.client.level.update_config(interaction.guild, self.data)
        await self.message.edit(embed=await self.update_embed(interaction, self.data))

    @button(label="Weekly Role", style=discord.ButtonStyle.gray, emoji="<:tgk_role:1073908306713780284>", row=3)
    async def weekly_role(self, interaction: Interaction, button: Button):
        view = Role_select(placeholder="Select the role you want to reward",min_values=1, max_values=1)
        view.value = False
        view.add_item(view)
        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()

        if not view.value: return
        self.data['weekly']['role'] = view.values[0].id
        await interaction.client.level.update_config(interaction.guild, self.data)
        await self.message.edit(embed=await self.update_embed(interaction, self.data))
        await interaction.delete_original_response()


        
    @button(label="Reward Roles", style=discord.ButtonStyle.gray, emoji="<:level_roles:1123938667212312637>", row=3)
    async def reward_roles(self, interaction: Interaction, button: Button):
        view = View()
        view.value = False
        view.select = Role_select(placeholder="Select the roles you want to reward",min_values=1, max_values=1)
        view.add_item(view.select)

        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()

        if not view.value: return await interaction.delete_original_message()
        modal = General_Modal(title="Enter Level", interaction=view.select.interaction)
        modal.level = TextInput(label="Reward Level",placeholder="Enter the level you want to reward", min_length=1, max_length=3)
        modal.add_item(modal.level)
        await view.select.interaction.response.send_modal(modal)

        await modal.wait()
        if not modal.value: return
        level = int(modal.level.value)
        role = view.select.values[0]
        self.data['rewards'][str(level)] = role.id
        await interaction.client.level.update_config(interaction.guild, self.data)
        await modal.interaction.response.edit_message(content=f"{role.mention} will now be rewarded at level {level}!", embed=None, view=None)
        await modal.interaction.delete_original_response()
        await self.message.edit(embed=await self.update_embed(interaction, self.data))