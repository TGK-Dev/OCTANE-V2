import discord
from discord.ext import commands
from discord import app_commands, Interaction
from utils.db import Document
from typing import TypedDict, List, Dict
from utils.views.modal import General_Modal
from utils.paginator import Paginator

class Notes(TypedDict):
    topic: str
    content: str

class NotepadData(TypedDict):
    _id: int
    user_id: int
    notes: Dict[str, Notes]

class UserCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.notepad = Document(self.bot.db, "notepad", NotepadData)

    async def note_auto(self, interaction: Interaction, current: str) -> List[app_commands.Choice]:
        user_data = await self.notepad.find(interaction.user.id)
        if not user_data:
            return [
                app_commands.Choice(name="No notepads found", value="No notepads found")
            ]
        return [
            app_commands.Choice(name=user_data['notes'][note]['topic'], value=user_data['notes'][note]['topic'])
            for note in user_data['notes'].keys()
        ][:24]
    
    async def item_autocomplete(self, interaction: discord.Interaction, string: str) -> List[app_commands.Choice[str]]:
        choices = []
        for item in self.bot.dank_items_cache.keys():
            if string.lower() in item.lower():
                choices.append(app_commands.Choice(name=item, value=item))
        if len(choices) == 0:
            return [
                app_commands.Choice(name=item, value=item)
                for item in self.bot.dank_items_cache.keys()
            ]
        else:
            return choices[:24]

    notepad = app_commands.Group(name="notepad", description="Notepad commands", allowed_installs=app_commands.AppInstallationType(guild=False, user=True), allowed_contexts=app_commands.AppCommandContext(dm_channel=True, guild=True, private_channel=True))

    @notepad.command(name="create", description="Create a new notepad")
    @app_commands.describe(topic="Notepad", content="Create a new notepad")
    async def create_notepad(self, interaction: Interaction, topic: str, content: str):
        user_data = await self.notepad.find(interaction.user.id)
        if not user_data:
            user_data = {'_id': interaction.user.id, 'user_id': interaction.user.id, 'notes': {}}
            await self.notepad.insert(user_data)
        user_data['notes'][topic] = {'topic': topic, 'content': content}
        await self.notepad.update(interaction.user.id, user_data)
        await interaction.response.send_message(f"Successfully created a new notepad with topic {topic}", ephemeral=True)

    @notepad.command(name="view", description="View your notepad")
    async def view_notepad(self, interaction: Interaction):
        user_data = await self.notepad.find(interaction.user.id)
        if not user_data:
            await interaction.response.send_message("You do not have a notepad", ephemeral=True)
            return
        pages = []
        for note, content in user_data['notes'].items():
            pages.append(discord.Embed(title=note, description=content['content']))
        if len(pages) == 0:
            await interaction.response.send_message("You do not have any notes", ephemeral=True)
            return
        await Paginator(interaction=interaction, pages=pages).start(embeded=True, timeout=60, quick_navigation=False, hidden=True)

    @notepad.command(name="delete", description="Delete a notepad")
    @app_commands.describe(topic="Notepad")
    @app_commands.autocomplete(topic=note_auto)
    async def delete_notepad(self, interaction: Interaction, topic: str):
        user_data = await self.notepad.find(interaction.user.id)
        if not user_data:
            await interaction.response.send_message("You do not have a notepad", ephemeral=True)
            return
        del user_data['notes'][topic]
        await self.notepad.update(interaction.user.id, user_data)
        await interaction.response.send_message(f"Succesfully deleted notepad with topic {topic}", ephemeral=True)

    @notepad.command(name="edit", description="Edit a notepad")
    @app_commands.describe(topic="Notepad")
    @app_commands.autocomplete(topic=note_auto)
    async def edit_notepad(self, interaction: Interaction, topic: str):
        user_data = await self.notepad.find(interaction.user.id)
        if not user_data:
            await interaction.response.send_message("You do not have a notepad", ephemeral=True)
            return
        
        note = user_data['notes'][topic]

        view = General_Modal(title=f"Editing notepad with topic {topic}", interaction=interaction)
        view.content = discord.ui.TextInput(label="New content", default=note['content'], required=True)
        view.add_item(view.content)

        await interaction.response.send_modal(view)
        await view.wait()

        if view.value is not True: return
        user_data['notes'][topic]['content'] = view.content.value
        
        await self.notepad.update(interaction.user.id, user_data)
        await view.interaction.response.send_message(f"Successfully edited notepad with topic {topic}", ephemeral=True)

    @app_commands.command(name="dank_calculator", description="Calculate the dankest meme")
    @app_commands.describe(item="The item you want to calculate", quantity="The quantity of the item you want to calculate")
    @app_commands.allowed_contexts(guilds=True, private_channels=True, dms=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.autocomplete(item=item_autocomplete)
    async def dank_calculator(self, interaction: Interaction, item: str, quantity: int):
        item_data = await self.bot.dank_items.find(item)
        if not item_data:
            await interaction.response.send_message("Item not found", ephemeral=True)
            return
        total = item_data['price'] * quantity
        await interaction.response.send_message(f"The total value of `{quantity}x` **{item}** is ⏣ `{total:,}`", ephemeral=True)

async def setup(bot):
    await bot.add_cog(UserCommands(bot))