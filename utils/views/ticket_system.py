import discord
from discord import Interaction, SelectOption
from discord.ui import View, Button, Select, button, Modal, TextInput
from .selects import Channel_select, Role_select, Color_Select

class Config_Edit(View):
    def __init__(self, user: discord.Member, data: dict, message: discord.Message=None):
        self.user = user
        self.data = data
        self.message = message
        super().__init__(timeout=120)
    
    def update_embed(self, data: dict):
        embed = discord.Embed(title="Ticket system configuration", color=0x363940)
        embed.add_field(name="Category", value=f"<#{data['category']}>" if data['category'] is not None else "None")
        embed.add_field(name="Channel", value=f"<#{data['channel']}>" if data['channel'] is not None else "None")
        embed.add_field(name="Logging", value=f"<#{data['logging']}>" if data['logging'] is not None else "None")
        embed.add_field(name="Panels", value=f"{len(data['panels'].keys())} panel(s)" if data['panels'] is not None else "None")
        embed.add_field(name="Last Panel Message ID", value=data['last_panel_message_id'] if data['last_panel_message_id'] is not None else "None")

        return embed
    
    @button(label="Category", style=discord.ButtonStyle.gray, emoji="<:category:1068484752664973324>")
    async def category(self, interaction: Interaction, button: Button):
        embed = discord.Embed(description="Select a category for the ticket system to use", color=0x363940)
        view = View()
        view.value = None
        view.select = Channel_select(placeholder="Select a category", min_values=1, max_values=1, channel_types=[discord.ChannelType.category])
        view.add_item(view.select)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True, delete_after=30)
        await view.wait()
        if view.value is None:
            await interaction.delete_original_message()
        else:
            await view.select.interaction.response.send_message("Category set!", ephemeral=True, delete_after=5)
            self.data["category"] = view.select.values[0].id
            embed = self.update_embed(self.data)
            for button in self.children: 
                if button.label == "Save": button.disabled = False
            await interaction.message.edit(embed=embed ,view=self)
    
    @button(label="Channel", style=discord.ButtonStyle.gray, emoji="<:channel:1017378607863181322>")
    async def channel(self, interaction: Interaction, button: Button):
        embed = discord.Embed(description="Select a channel for the ticket system to use", color=0x363940)
        view = View()
        view.value = None
        view.select = Channel_select(placeholder="Select a channel", min_values=1, max_values=1, channel_types=[discord.ChannelType.text])
        view.add_item(view.select)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True, delete_after=30)
        await view.wait()
        if view.value is None:
            await interaction.delete_original_message()
        else:
            await view.select.interaction.response.send_message("Channel set!", ephemeral=True, delete_after=5)
            self.data["channel"] = view.select.values[0].id
            embed = self.update_embed(self.data)
            for button in self.children: 
                if button.label == "Save": button.disabled = False
            await interaction.message.edit(embed=embed ,view=self)
    
    @button(label="Logging", style=discord.ButtonStyle.gray, emoji="<:logging:1017378971140235354>")
    async def logging(self, interaction: Interaction, button: Button):
        embed = discord.Embed(description="Select a channel for the ticket system to log to", color=0x363940)
        view = View()
        view.value = None
        view.select = Channel_select(placeholder="Select a channel", min_values=1, max_values=1, channel_types=[discord.ChannelType.text])
        view.add_item(view.select)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True, delete_after=30)
        await view.wait()
        if view.value is None:
            await interaction.delete_original_message()
        else:
            await view.select.interaction.response.send_message("Logging channel set!", ephemeral=True, delete_after=5)
            self.data["logging"] = view.select.values[0].id
            embed = self.update_embed(self.data)
            for button in self.children: 
                if button.label == "Save": button.disabled = False
            await interaction.message.edit(embed=embed ,view=self)
    
    async def on_timeout(self):
        for button in self.children: button.disabled = True
        await self.message.edit(view=self)
    
    async def on_error(self, error, item, interaction):
        try:
            await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True, delete_after=5)
        except:
            await interaction.edit_original_message(content=f"An error occurred: {error}", view=self)

    async def interaction_check(self, interaction: Interaction):
        if interaction.user.id == self.user.id:
            return True
        else:
            await interaction.response.send_message("You are not allowed to use this view", ephemeral=True, delete_after=5)
            return False

class Panel_Edit(View):
    def __init__(self, user: discord.Member, data:dict, message: discord.Message=None):
        self.user = user
        self.data = data
        self.message = message
        super().__init__(timeout=120)
    
    def update_embed(self, data:dict):
        embed = discord.Embed(title=f"Settings for Panel: {data['key']}", color=0x363940, description="")
        embed.description += f"**Support Roles:** {', '.join([f'<@&{role}>' for role in data['support_roles']]) if len(data['support_roles']) > 0 else '`None`'}\n"
        embed.description += f"**Ping Role:**" + (f" <@&{data['ping_role']}>" if data['ping_role'] is not None else "`None`") + "\n"
        embed.description += f"**Description:**" + (f"```\n{data['description']}\n```" if data['description'] is not None else "`None`") + "\n"
        embed.description += f"**Emoji:**" + (f" {data['emoji']}" if data['emoji'] is not None else "`None`") + "\n"
        embed.description += f"**Color:**" + (f" {data['color']}" if data['color'] is not None else "`None`") + "\n"
        embed.description += f"**Modal:** " + (f" Type: {data['modal']['type']}") + (f"```\n{data['modal']['question']}\n```" if data['modal']['question'] is not None else "`None`") + "\n"
        return embed
    
    @button(label="Support Roles", style=discord.ButtonStyle.gray, emoji="<:managers:1017379642862215189>", row=0)
    async def support_roles(self, interaction: Interaction, button: Button):
        embed = discord.Embed(description="Select the roles that can use the panel", color=0x363940)
        view = View()
        view.value = None
        view.select = Role_select(placeholder="Select roles", min_values=1, max_values=10)
        view.add_item(view.select)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True, delete_after=30)
        await view.wait()
        if view.value is None:
            await interaction.delete_original_response()
        else:
            await view.select.interaction.response.send_message("Support roles set!", ephemeral=True, delete_after=5)
            await interaction.delete_original_response()
            self.data["support_roles"] = [role.id for role in view.select.values]
            embed = self.update_embed(self.data)
            for button in self.children: 
                if button.label == "Save": button.disabled = False
            await interaction.message.edit(embed=embed ,view=self)
    
    @button(label="Ping Role", style=discord.ButtonStyle.gray, emoji="<:role_mention:1063755251632582656>", row=0)
    async def ping_role(self, interaction: Interaction, button: Button):
        embed = discord.Embed(description="Select the role to ping when the panel is used", color=0x363940)
        view = View()
        view.value = None
        view.select = Role_select(placeholder="Select a role", min_values=1, max_values=1)
        view.add_item(view.select)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True, delete_after=30)
        await view.wait()
        if view.value is None:
            await interaction.delete_original_response()
        else:
            await view.select.interaction.response.send_message("Ping role set!", ephemeral=True, delete_after=5)
            await interaction.delete_original_response()
            self.data["ping_role"] = view.select.values[0].id
            embed = self.update_embed(self.data)
            for button in self.children: 
                if button.label == "Save":
                    button.disabled = False
            await interaction.message.edit(embed=embed ,view=self)

    @button(label="Description", style=discord.ButtonStyle.gray, emoji="<:description:1063755251632582656>", row=1)
    async def description(self, interaction: Interaction, button: Button):
        modal = Panel_Description_Modal(self.data)
        qestion = TextInput(label="Set the description for the panel", max_length=300)
        if self.data["description"] is not None:qestion.value = self.data["description"]
        else: qestion.placeholder = "Enter a description"
        modal.add_item(qestion)
        await interaction.response.send_modal(modal)
        await modal.wait()

        if modal.value:
            embed = self.update_embed(self.data)
            for button in self.children: 
                if button.label == "Save": button.disabled = False
            await modal.interaction.response.send_message("Description set!", ephemeral=True, delete_after=5)
            await interaction.message.edit(embed=embed ,view=self)

    @button(label="Emoji", style=discord.ButtonStyle.gray, emoji="<:embed:1017379990289002536>", row=1)
    async def emoji(self, interaction: Interaction, button: Button):
        modal = Panel_emoji(self.data)
        qestion = TextInput(label="Set the emoji for the panel", max_length=300)
        if self.data["emoji"] is not None:qestion.value = self.data["emoji"]
        else: qestion.placeholder = "Enter an emoji"
        modal.add_item(qestion)
        await interaction.response.send_modal(modal)
        await modal.wait()

        if modal.value:
            embed = self.update_embed(self.data)
            for button in self.children: 
                if button.label == "Save": button.disabled = False
            await modal.interaction.response.send_message("Emoji set!", ephemeral=True, delete_after=5)
            await interaction.message.edit(embed=embed ,view=self)

    @button(label="Color", style=discord.ButtonStyle.gray, emoji="<:color:1017379990289002536>", row=1)
    async def color(self, interaction: Interaction, button: Button):
        embed = discord.Embed(description="Select the color for the panel", color=0x363940)
        view = View()
        view.value = None
        view.select = Color_Select()
        view.add_item(view.select)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True, delete_after=30)
        await view.wait()
        if view.value:
            await view.select.interaction.response.send_message("Color set to " + view.select.values[0], ephemeral=True, delete_after=5)
            await interaction.delete_original_response()
            self.data["color"] = view.select.values[0]
            embed = self.update_embed(self.data)
            for button in self.children: 
                if button.label == "Save": button.disabled = False
            await interaction.message.edit(embed=embed ,view=self)
    
    @button(label="Questionnaire", style=discord.ButtonStyle.gray, emoji="<:StageIconRequests:1005075865564106812>", row=2)
    async def questionnaire(self, interaction: Interaction, button: Button):
        modal = Question_Modal(self.data)
        qestion_type = TextInput(label="Set type of asnwer", max_length=20)

        if self.data["modal"]["type"] is not None:qestion_type.placeholder = "Avable types: (long,short)"
        else: qestion_type.default = "short"
        qestion = TextInput(label="Set the question for the panel", max_length=300)
        if self.data["modal"]["question"] is not None:qestion.default = self.data["modal"]["question"]
        else: qestion.placeholder = "Enter a question"

        modal.add_item(qestion_type)
        modal.add_item(qestion)
        await interaction.response.send_modal(modal)
        await modal.wait()

        if modal.value:
            embed = self.update_embed(self.data)
            for button in self.children: 
                if button.label == "Save": button.disabled = False
            await modal.interaction.response.send_message("Question set!", ephemeral=True, delete_after=5)
            await interaction.message.edit(embed=embed ,view=self)

    @button(label="Save", style=discord.ButtonStyle.green, emoji="<:save:1068611610568040539>", disabled=True)
    async def save(self, interaction: Interaction, button: Button):
        for button in self.children: button.disabled = True
        await interaction.response.send_message(content="Saved!", delete_after=4, ephemeral=True)
        await interaction.client.tickets.config.update(self.data)
        await interaction.message.edit(view=self)


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
