import discord
from discord.ext import commands
from typing import Any, List, Union
from discord import Interaction, SelectOption
from discord.interactions import Interaction
from discord.ui import View, Button, Select
from discord.ui.item import Item
from .selects import Role_select, Channel_select, Select_General
from .modal import General_Modal
from utils.paginator import Paginator


class Giveaway(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    async def on_error(self, interaction: Interaction, error: Exception, item: Item):
        return await interaction.followup.send(content=f"An error occured: {error}", ephemeral=True)

    @discord.ui.button(emoji="<a:tgk_tadaa:806631994770849843>", style=discord.ButtonStyle.gray, custom_id="giveaway:Join")
    async def _join(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True, ephemeral=True)
        data = await interaction.client.giveaway.get_giveaway(interaction.message)
        if data is None: await interaction.followup.send("This giveaway is not available anymore.", ephemeral=True)
        config = await interaction.client.giveaway.get_config(interaction.guild)

        user_roles = [role.id for role in interaction.user.roles]
        if (set(user_roles) & set(config["blacklist"])): 
            embed = discord.Embed(description="Unable to join the giveawy due to blacklisted role.", color=discord.Color.red())
            return await interaction.followup.send(embed=embed, ephemeral=True)

        if str(interaction.user.id) in data['entries'].keys():
            view = GiveawayLeave(data, interaction.user, interaction)
            embed = discord.Embed(description="You already joined this giveaway.",color=interaction.client.default_color)
            return await interaction.followup.send(embed=embed, view=view)
        
        result = {}
        if data['ended']: return await interaction.followup.send("This giveaway has ended.", ephemeral=True)
        if data['req_level'] or data['req_weekly']:
            user_level = await interaction.client.level.get_member_level(interaction.user)

            if data['req_level']:
                if user_level['level'] >= data['req_level']: 
                    pass
                else:
                    result['level'] = f"You don't have the required level to join this giveaway.\n> `Required levels: {data['req_level']}`"

            if data['req_weekly']:
                if user_level['weekly'] >= data['req_weekly']:
                    pass
                else:
                    result['weekly'] = "You don't have the required weekly XP to join this giveaway.\n> `Required weekly XP: {}`".format(data['req_weekly'])
        
        if data['req_roles']:
            if set(data['req_roles']) <= set(user_roles):
                pass
            else:
                missing_roles = set(data['req_roles']) - set(user_roles)
                missing_roles = [f"<@&{role}>" for role in missing_roles]
                result['roles'] = f"You don't have the required role(s) to join this giveaway.\n> Missing roles: {', '.join(missing_roles)}"

        if data['channel_messages'] != {}:
            user_level = await interaction.client.level.get_member_level(interaction.user)
            channel = str(data['channel_messages']['channel'])
            if channel not in user_level['messages'].keys():
                result['messages'] = f"You don't have the required messages to join this giveaway.\n> Required messages: Must sent {data['channel_messages']['count']} messages in <#{channel}>"
            elif channel in user_level['messages'].keys():
                if user_level['messages'][channel] < data['channel_messages']['count']:
                    result['messages'] = f"You don't have the required messages to join this giveaway.\n> Required messages: Must sent {data['channel_messages']['count']} messages in <#{channel}>"

        bypassed = False    
        if len(result.keys()) > 0:
            if data['bypass_role'] and (set(user_roles) & set(data['bypass_role'])):
                bypassed = True
                pass
            elif set(user_roles) & set(config['global_bypass']):
                bypassed = True
                pass
            else:
                embed = discord.Embed(description="", title="You Failed to meet the following requriements")
                i = 1
                for key, value in result.items():
                    embed.description += f"{i}. {value}\n"
                    i += 1
                embed.color = discord.Color.red()
                return await interaction.followup.send(embed=embed, ephemeral=True)
        
        entries = 1
        for key, value in config['multipliers'].items():
            if int(key) in user_roles:
                entries += value
        
        data['entries'][str(interaction.user.id)] = entries
        await interaction.client.giveaway.update_giveaway(interaction.message, data)
        embed = discord.Embed(description="You have successfully joined the giveaway.", color=discord.Color.green())
        if bypassed:
            embed.description += "\nYou have bypassed the requirements due to your bypass role."       
        await interaction.followup.send(embed=embed)

    @discord.ui.button(label="Participants", style=discord.ButtonStyle.gray, emoji="<:tgk_entries:1124995375548338176>", custom_id="giveaway:Entries")
    async def _entries(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = await interaction.client.giveaway.get_giveaway(interaction.message)
        if data is None: return await interaction.followup.send("This giveaway is not available anymore/invalid.", ephemeral=True)
        if len(data['entries'].keys()) == 0: return await interaction.response.send_message("No one has joined this giveaway yet.", ephemeral=True)
        entries = data['entries']
        entries = sorted(entries.items(), key=lambda x: x[1], reverse=True)
        entries = [entries[i:i + 10] for i in range(0, len(entries), 10)]
        pages = []
        i = 1
        for page in entries:
            embed = discord.Embed(title="Giveaway Participants", description="", color=interaction.client.default_color)
            for user in page:
                embed.description += f"{i}. <@{user[0]}>\n"                
                i += 1
            try:
                embed.set_footer(text=f"Your Entries: {data['entries'][str(interaction.user.id)]}")
            except:
                pass
            pages.append(embed)
        
        await Paginator(interaction, pages).start(embeded=True, hidden=True, quick_navigation=False)

class GiveawayLeave(View):
    def __init__(self, data: dict, user: discord.Member, interaction: discord.Interaction):
        self.data = data
        self.user = user
        self.interaction = interaction
        super().__init__(timeout=30)
    
    async def on_timeout(self):
        await self.interaction.delete_original_response()
    
    @discord.ui.button(label="View your chances", style=discord.ButtonStyle.gray, emoji="<:tgk_entries:1124995375548338176>", custom_id="giveaway:Chances")
    async def _chances(self, interaction: discord.Interaction, button: discord.ui.Button):
        entries: List[int] = []
        for key, value in self.data['entries'].items():
            if int(key) in entries: continue
            entries.extend([int(key)] * value)
        percentage = round(entries.count(self.user.id) / len(entries) * 100, 2)
        embed = discord.Embed(description=f"You have a *{percentage}%* chance of winning this giveaway.", color=interaction.client.default_color)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Leave", style=discord.ButtonStyle.gray, emoji="<:tgk_pepeexit:790189030569934849>", custom_id="giveaway:Leave")
    async def _leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            del self.data['entries'][str(self.user.id)]
            await interaction.client.giveaway.update_giveaway(interaction.message, self.data)
        except:
            pass
        await interaction.response.edit_message(content="You have successfully left the giveaway.", view=None, delete_after=10, embed=None)        
    

class GiveawayConfig(View):
    def __init__(self, data: dict, user: discord.Member, message: discord.Message=None):
        self.data = data
        self.user = user
        self.message = message
        super().__init__(timeout=120)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id == self.user.id:
            return True
        else:
            return False
    
    async def update_embed(self, interaction: discord.Interaction, giveaway_data: dict):
        embed = discord.Embed(title=f"{interaction.guild.name} Giveaway Config", color=interaction.client.default_color, description="")
        embed.description += f"**Manager Roles:** {', '.join([f'<@&{role}>' for role in giveaway_data['manager_roles']]) if len(giveaway_data['manager_roles']) > 0 else '`None`'}\n"
        embed.description += f"**Logging Channel:** {interaction.guild.get_channel(giveaway_data['log_channel']).mention if giveaway_data['log_channel'] else '`None`'}\n"
        embed.description += f"**Dm Message:** ```\n{giveaway_data['dm_message']}\n```\n"
        embed.description += f"**Blacklist:**\n {', '.join([f'<@&{(role)}>' for role in giveaway_data['blacklist']]) if len(giveaway_data['blacklist']) > 0 else '`None`'}\n"
        embed.description += f"**Global Bypass:**\n {', '.join([f'<@&{(role)}>' for role in giveaway_data['global_bypass']]) if len(giveaway_data['global_bypass']) > 0 else '`None`'}\n"
        mults = giveaway_data['multipliers']                
        mults = sorted(mults.items(), key=lambda x: int(x[1]))
        embed.description += f"\n**Multipliers:**\n"
        for value, multi in mults:
            embed.description += f"> `{multi}` : <@&{value}>\n"
        return embed
    
    @discord.ui.button(label="Manager Roles", style=discord.ButtonStyle.gray, emoji="<:tgk_role:1073908306713780284>", custom_id="giveaway:ManagerRoles")
    async def _manager_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = View()
        view.value = None
        view.select = Role_select(placeholder="Please select the roles you want to add/remove.", min_values=1, max_values=10)
        view.add_item(view.select)
        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()

        if view.value is None:
            return await interaction.delete_original_response()
        added = ""
        removed = ""
        for role in view.select.values:
            if role.id not in self.data['manager_roles']:
                self.data['manager_roles'].append(role.id)
                added += f"<@&{role.id}> "
            else:
                self.data['manager_roles'].remove(role.id)
                removed += f"<@&{role.id}> "
        await view.select.interaction.response.edit_message(content=f"Added: {added}\nRemoved: {removed}", view=None)
        await interaction.delete_original_response()
        await interaction.message.edit(embed=await self.update_embed(interaction, self.data))
        await interaction.client.giveaway.update_config(interaction.guild, self.data)
    
    @discord.ui.button(label="Logging Channel", style=discord.ButtonStyle.gray, emoji="<:tgk_channel:1073908465405268029>", custom_id="giveaway:LoggingChannel", row=1)
    async def _logging_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = View()
        view.value = None
        view.select = Channel_select(placeholder="Please select the channel you want to set as logging channel.", min_values=1, max_values=1, channel_types=[discord.ChannelType.text])
        view.add_item(view.select)
        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()

        if view.value is None:
            return await interaction.delete_original_response()
        self.data['log_channel'] = view.select.values[0].id
        await view.select.interaction.response.edit_message(content=f"Set logging channel to {view.select.values[0].mention}", view=None)
        await interaction.delete_original_response()
        await interaction.message.edit(embed=await self.update_embed(interaction, self.data))
        await interaction.client.giveaway.update_config(interaction.guild, self.data)

    @discord.ui.button(label="Dm Message", style=discord.ButtonStyle.gray, emoji="<:tgk_edit:1073902428224757850>", custom_id="giveaway:DmMessage", row=1)
    async def _dm_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = General_Modal(title="Giveaway Dm Message", interaction=interaction)
        view.value = None
        view.input = discord.ui.TextInput(label="Message",placeholder="Please enter the message you want to set as dm message.", min_length=1, max_length=300, style=discord.TextStyle.long)
        if self.data['dm_message']:
            view.input.default = str(self.data['dm_message'])
        view.add_item(view.input)
        await interaction.response.send_modal(view)
        await view.wait()

        if view.value is None: return
        self.data['dm_message'] = str(view.input.value)
        await view.interaction.response.edit_message(embed=await self.update_embed(interaction, self.data))
        await interaction.client.giveaway.update_config(interaction.guild, self.data)

    @discord.ui.button(label="Global Bypass", style=discord.ButtonStyle.gray, emoji="<:tgk_role:1073908306713780284>", custom_id="giveaway:GlobalBypass", row=0)
    async def _global_bypass(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = View()
        view.value = None
        view.select = Role_select(placeholder="Please select the roles you want to add/remove.", min_values=1, max_values=10)
        view.add_item(view.select)
        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()

        if view.value is None:
            return await interaction.delete_original_response()
        added = ""
        removed = ""

        for role in view.select.values:
            if role.id not in self.data['global_bypass']:
                self.data['global_bypass'].append(role.id)
                added += f"<@&{role.id}> "
            else:
                self.data['global_bypass'].remove(role.id)
                removed += f"<@&{role.id}> "
        await view.select.interaction.response.edit_message(content=f"Added: {added}\nRemoved: {removed}", view=None)
        await interaction.delete_original_response()
        await interaction.message.edit(embed=await self.update_embed(interaction, self.data))
        await interaction.client.giveaway.update_config(interaction.guild, self.data)

    @discord.ui.button(label="Blacklist", style=discord.ButtonStyle.gray, emoji="<:tgk_role:1073908306713780284>", custom_id="giveaway:Blacklist", row=0)
    async def _blacklist(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = View()
        view.value = None
        view.select = Role_select(placeholder="Please select the roles you want to add/remove.", min_values=1, max_values=10)
        view.add_item(view.select)
        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()

        if view.value is None:
            return await interaction.delete_original_response()
        added = ""
        removed = ""
        for role in view.select.values:
            if role.id not in self.data['blacklist']:
                self.data['blacklist'].append(role.id)
                added += f"<@&{role.id}> "
            else:
                self.data['blacklist'].remove(role.id)
                removed += f"<@&{role.id}> "
        await view.select.interaction.response.edit_message(content=f"Added: {added}\nRemoved: {removed}", view=None)
        await interaction.delete_original_response()
        await interaction.message.edit(embed=await self.update_embed(interaction, self.data))
        await interaction.client.giveaway.update_config(interaction.guild, self.data)

    
    @discord.ui.button(label="Multipliers", style=discord.ButtonStyle.gray, emoji="<:tgk_role:1073908306713780284>", custom_id="giveaway:Multipliers", row=0)
    async def _multipliers(self, interaction: discord.Interaction, button: discord.ui.Button):
        multi_view = View()
        multi_view.value = None
        multi_view.select = Select_General(interaction, options=[SelectOption(label="Remove", value="0"),SelectOption(label="1x", value="1"), SelectOption(label="2x", value="2"), SelectOption(label="3x", value="3"), SelectOption(label="4x", value="4"), SelectOption(label="5x", value="5"), SelectOption(label="6x", value="6"), SelectOption(label="7x", value="7"), SelectOption(label="8x", value="8"), SelectOption(label="9x", value="9"), SelectOption(label="10x", value="10")], placeholder="Select the multiplier you want to set",min_values=1, max_values=1)
        multi_view.add_item(multi_view.select)
        await interaction.response.send_message(view=multi_view, ephemeral=True)
        await multi_view.wait()
        if not multi_view.value: return await interaction.delete_original_message()
        multiplier = int(multi_view.select.values[0])

        roles_view = View()
        roles_view.value = None
        roles_view.select = Role_select(placeholder="Select the role you want to set multiplier for", min_values=1, max_values=15)
        roles_view.add_item(roles_view.select)
        await multi_view.select.interaction.response.edit_message(view=roles_view)
        await roles_view.wait()
        if not roles_view.value: return await interaction.delete_original_message()
        roles = roles_view.select.values
        if multiplier == 0:
            for role in roles:
                    try:
                        del self.data['multipliers'][str(role.id)]
                    except KeyError:
                        pass
            await roles_view.select.interaction.response.edit_message(content=f"Removed multiplier for {', '.join([f'<@&{role.id}>' for role in roles])}", view=None)
        else:
            for role in roles:
                self.data['multipliers'][str(role.id)] = multiplier
            await roles_view.select.interaction.response.edit_message(content=f"Set multiplier for {', '.join([f'<@&{role.id}>' for role in roles])} to {multiplier}x", view=None, delete_after=5)
            await interaction.message.edit(embed=await self.update_embed(interaction, self.data))
        await interaction.client.giveaway.update_config(interaction.guild, self.data)