import discord
from discord.ui import View, Select
from discord import SelectOption
from discord import Interaction


class Channel_select(discord.ui.ChannelSelect):
    def __init__(self, placeholder, min_values, max_values, channel_types, *, disabled=False):
        self.interaction = None
        self.value = False
        super().__init__(placeholder=placeholder, min_values=min_values, max_values=max_values, channel_types=channel_types, disabled=disabled)
    
    async def callback(self, interaction: discord.Interaction):
        self.interaction = interaction
        self.view.value = True
        self.view.stop()

class Mention_select(discord.ui.MentionableSelect):
    def __init__(self, placeholder, min_values, max_values, *, disabled=False):
        self.interaction = None
        self.value = False
        super().__init__(placeholder=placeholder, min_values=min_values, max_values=max_values, disabled=disabled)
    
    async def callback(self, interaction: discord.Interaction):
        self.interaction = interaction
        self.view.value = True
        self.view.stop()

class Role_select(discord.ui.RoleSelect):
    def __init__(self, placeholder, min_values, max_values, *, disabled=False):
        self.interaction = None
        self.value = False
        super().__init__(placeholder=placeholder, min_values=min_values, max_values=max_values, disabled=disabled)
    
    async def callback(self, interaction: discord.Interaction):
        self.interaction = interaction
        self.view.value = True
        self.view.stop()
    
class Color_Select(Select):
    def __init__(self, interaction: Interaction=None):
        self.interaction = None
        self.value = None
        super().__init__(placeholder="Select a color",max_values=1, options=[SelectOption(label="Red", value="red", emoji="🟥", description="Red color"),SelectOption(label="Yellow", value="yellow", emoji="🟨", description="Yellow color"),SelectOption(label="Green", value="green", emoji="🟩", description="Green color"),SelectOption(label="Blurple", value="blurple", emoji="🔵", description="Blurple color")])

    async def callback(self, interaction: Interaction):
        self.interaction = interaction
        self.view.value = True
        self.view.stop()