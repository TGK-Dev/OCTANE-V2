import discord
from discord import Interaction, TextStyle
from discord.ui import View, Modal


class Question_Modal(Modal):
    def __init__(self, data, interaction: Interaction=None):
        self.interaction = interaction
        self.data = data
        self.value = None
        super().__init__(timeout=120, title=f"Question for Panel {data['key']}")
    
    async def on_submit(self, interaction: Interaction):
        self.data["modal"]["type"] = self.children[0]
        self.data["modal"]["question"] = self.children[1]
        self.value = True
        self.interaction = interaction
        self.stop()
        
class Panel_Description_Modal(Modal):
    def __init__(self, data, interaction: Interaction=None):
        self.interaction = interaction
        self.data = data
        self.value = None
        super().__init__(timeout=120, title=f"Description for Panel {data['key']}")

    async def on_submit(self, interaction: Interaction):
        self.data["description"] = self.children[0]
        self.value = True
        self.interaction = interaction
        self.stop()

class Panel_emoji(Modal):
    def __init__(self, data, interaction: Interaction=None):
        self.interaction = interaction
        self.data = data
        self.value = None
        super().__init__(timeout=120, title=f"Emoji for Panel {data['key']}")

    async def on_submit(self, interaction: Interaction):
        self.data["emoji"] = self.children[0]
        self.value = True
        self.interaction = interaction
        self.stop()

class Panel_Question(Modal):
    def __init__(self, title: str, interaction: Interaction=None):
        super().__init__(timeout=120, title=title)
        self.interaction = interaction
        self.value = None

    async def on_submit(self, interaction: Interaction):
        self.value = True
        self.interaction = interaction
        self.stop()

class Panel_Partnership(Modal):
    def __init__(self, data, interaction: Interaction=None):
        self.interaction = interaction
        self.data = data
        self.value = None
        super().__init__(timeout=120, title=f"Partnership for Panel {data['key']}")

    async def on_submit(self, interaction: Interaction):
        self.data["partnership"] = self.children[0]
        self.value = True
        self.interaction = interaction
        self.stop()

class General_Modal(Modal):
    def __init__(self, title: str, interaction: Interaction=None, **kwargs):
        super().__init__(timeout=120, title=title, **kwargs)
        self.interaction = interaction
        self.value = None

    async def on_submit(self, interaction: Interaction):
        self.value = True
        self.interaction = interaction
        self.stop()