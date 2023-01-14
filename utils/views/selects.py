import discord


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