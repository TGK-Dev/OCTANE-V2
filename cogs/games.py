import discord
import aiohttp
import datetime
from discord import app_commands, Interaction
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageChops
from io import BytesIO
from utils.views.type_race import TyperaceView

class Games(commands.GroupCog, name="game"):
    def __init__(self, bot):
        self.bot = bot
        self.bot.type_race_cache = {}

    async def get_quote(self):
        url = "https://api.quotable.io/random?minLength=200&maxLength=250"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                

    async def get_image(self, data):
        #crate a image which can contain the quote and quote lenth max 250 and min 200 image is transparent
        img = Image.new("RGBA", (600, 300), (0, 0, 0, 0))
        font = ImageFont.truetype("./assets/fonts/arial.ttf", 30)
        draw = ImageDraw.Draw(img)
        #split the quote into lines archive the max width of the image
        lines = []
        line = ""
        for word in data["content"].split():
            if font.getsize(line + word)[0] < 500:
                line += f" {word}"
            else:
                lines.append(line)
                line = word
        lines.append(line)
        #draw the quote on the image
        y_text = 0
        for line in lines:
            width, height = font.getsize(line)
            draw.text(((600 - width) / 2, y_text), line, font=font, fill="white")
            y_text += height

        buffer = BytesIO()
        img.save(buffer, "png")
        buffer.seek(0)
        return buffer

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot: return
        if not message.guild: return
        if message.channel.id not in self.bot.type_race_cache.keys(): return
        if message.content.startswith(("ig.", "gk.", "!", "-")): return
        self.bot.dispatch("typerace", message)
    
    @commands.Cog.listener()
    async def on_typerace(self, message: discord.Message):
        channel = message.channel
        data = self.bot.type_race_cache[channel.id]
        if not data: return
        if not data["started"]: return
        start = data["start"]
        end = datetime.datetime.utcfromtimestamp(message.created_at.timestamp())
        user_data = {
                "_id": message.author.id,
                "time": (end - start).total_seconds(),
                "content": message.content,
                "acuracy": 0,
                "wpm": 0,
        }
        await message.delete()
        correct_words = 0
        for word1, word2 in zip(data["content"].split(), message.content.split()):
            if word1 == word2:
                correct_words += 1
        accuracy = correct_words / len(data["content"].split()) * 100

        wpm = len(message.content.split()) / user_data["time"] * 60
        user_data["wpm"] = round(wpm)
        user_data["acuracy"] = round(accuracy)
        data["participants"][message.author.id] = user_data
        self.bot.type_race_cache[channel.id] = data
        await channel.send(f"{message.author.mention} You have completed the typerace with {round(wpm)} wpm and {round(accuracy)}% accuracy", delete_after=10)

    @app_commands.command(name="typerace", description="Start a typerace game")
    async def typerace(self, interaction: Interaction):
        if interaction.channel.id in self.bot.type_race_cache.keys():
            return await interaction.response.send_message("There is already a game running in this channel", ephemeral=True)
        content = await self.get_quote()
        print(content)
        image = await self.get_image(content)
        embed = discord.Embed(title="Typerace", description="", color=interaction.client.default_color)
        embed.description = f"Type the following quote as fast as you can and as accurate as you can\n"
        embed.description += "Add `ig.` At start of your message to ignore the game\n"
        view = TyperaceView(content, image)
        await interaction.response.send_message(embed=embed, view=view)
        message = await interaction.original_response()
        data = {
            "_id": interaction.channel.id,
            "message_id": message.id,
            "started": False,
            "host": interaction.user.id,
            "message": message,
            "participants": {},
            "start": None,
            "content": content["content"],
            "channel": message.channel.id
        }
        self.bot.type_race_cache[interaction.channel.id] = data
    

async def setup(bot):
    await bot.add_cog(Games(bot))

    
