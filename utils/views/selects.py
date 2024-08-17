import discord
from discord.ui import View, Select, select, button
from discord import SelectOption
from discord import Interaction
from typing import Literal


class Channel_select(discord.ui.ChannelSelect):
    def __init__(
        self,
        placeholder: str,
        min_values: int,
        max_values: int,
        channel_types: list[discord.ChannelType],
        *,
        disabled=False,
    ):
        self.interaction = None
        self.value = False
        super().__init__(
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values,
            channel_types=channel_types,
            disabled=disabled,
        )

    async def callback(self, interaction: discord.Interaction):
        self.interaction = interaction
        self.view.value = True
        self.view.stop()


class Mention_select(discord.ui.MentionableSelect):
    def __init__(
        self, placeholder: str, min_values: int, max_values: int, *, disabled=False
    ):
        self.interaction = None
        self.value = False
        super().__init__(
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values,
            disabled=disabled,
        )

    async def callback(self, interaction: discord.Interaction):
        self.interaction = interaction
        self.view.value = True
        self.view.stop()


class Role_select(discord.ui.RoleSelect):
    def __init__(self, placeholder: str, min_values: int, max_values: int, *, disabled=False):
        self.interaction = None
        self.value = False
        super().__init__(
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values,
            disabled=disabled,
        )

    async def callback(self, interaction: discord.Interaction):
        self.interaction = interaction
        self.view.value = True
        self.view.stop()


class User_Select(discord.ui.UserSelect):
    def __init__(self, placeholder: str, min_values: int, max_values: int, *, disabled=False):
        self.interaction = None
        self.value = False
        super().__init__(
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values,
            disabled=disabled,
        )

    async def callback(self, interaction: discord.Interaction):
        self.interaction = interaction
        self.view.value = True
        self.view.stop()


class Color_Select(Select):
    def __init__(self, interaction: Interaction = None):
        self.interaction = None
        self.value = None
        super().__init__(
            placeholder="Select a color",
            max_values=1,
            options=[
                SelectOption(
                    label="Red", value="red", emoji="🟥", description="Red color"
                ),
                SelectOption(
                    label="Yellow",
                    value="yellow",
                    emoji="🟨",
                    description="Yellow color",
                ),
                SelectOption(
                    label="Green", value="green", emoji="🟩", description="Green color"
                ),
                SelectOption(
                    label="Blurple",
                    value="blurple",
                    emoji="🔵",
                    description="Blurple color",
                ),
            ],
        )

    async def callback(self, interaction: Interaction):
        self.interaction = interaction
        self.view.value = True
        self.view.stop()


class Select_General(Select):
    def __init__(self, interaction: Interaction = None, options: list = None, **kwargs):
        self.interaction = None
        self.value = None
        super().__init__(options=options, **kwargs)

    async def callback(self, interaction: Interaction):
        self.interaction = interaction
        self.view.value = True
        self.view.stop()


class Emoji_Select(View):
    def __init__(
        self,
        user: discord.Member,
        guild: discord.Guild,
        type: Literal["animated", "static"] = "static",
    ):
        self.user = user
        self.guild = guild
        self.type = type
        self.current_page = 0
        self.total_pages = 0

    def get_emojis(self, type: Literal["animated", "static"], index: int):
        static_emojis = [emoji for emoji in self.guild.emojis if not emoji.animated]
        animated_emojis = [emoji for emoji in self.guild.emojis if emoji.animated]

        ## divide the emojis into pages of 24

        static_emojis = [
            static_emojis[i : i + 24] for i in range(0, len(static_emojis), 24)
        ]
        animated_emojis = [
            animated_emojis[i : i + 24] for i in range(0, len(animated_emojis), 24)
        ]

        if type == "static":
            if index > len(static_emojis):
                return static_emojis[0]
            return static_emojis[index]
        elif type == "animated":
            if index > len(animated_emojis):
                return animated_emojis[0]
            return animated_emojis[index]

    def create_options(self, emojis: list):
        options = []
        self.total_pages = len(emojis)
        for emoji in emojis:
            options.append(
                SelectOption(label=emoji.name, value=emoji.id, emoji=str(emoji))
            )
        return options[:24]

    @select(
        placeholder="Select an emoji",
        min_values=1,
        max_values=1,
        options=[
            SelectOption(label="Animated", value="animated", emoji="🎥"),
            SelectOption(label="Static", value="static", emoji="🖼️"),
        ],
    )
    async def _type(self, interaction: Interaction, select: Select):
        pass

    @button(
        style=discord.ButtonStyle.gray, emoji="<:tgk_rightarrow:1088526714205917325>"
    )
    async def _right(self, interaction: Interaction, button: discord.Button):
        emojis = self.get_emojis(self.type, self.current_page + 1)
        self.current_page += 1
        options = self.create_options(emojis)
        self.children[0].options = options
        await interaction.response.edit_message(view=self)

    @button(
        label="Change Type",
        style=discord.ButtonStyle.gray,
        emoji="<:tgk_refresh:1171330950416842824>",
    )
    async def _change_type(self, interaction: Interaction, button: discord.Button):
        pass

    @button(
        style=discord.ButtonStyle.gray, emoji="<:tgk_leftarrow:1088526575781285929>"
    )
    async def _left(self, interaction: Interaction, button: discord.Button):
        emojis = self.get_emojis(self.type, self.current_page - 1)
        self.current_page -= 1
        options = self.create_options(emojis)
        self.children[0].options = options
        await interaction.response.edit_message(view=self)
