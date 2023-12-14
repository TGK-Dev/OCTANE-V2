import discord 
import re
from discord import app_commands
from discord.ext import commands

night_pattern = re.compile(r"Night ([1-9]|1[0-5])")

class Mafia(commands.GroupCog):
    def __init__(self, bot):
        self.bot = bot
        self.mafia_channels = {}
        self.mafia_inprosses = []

    @commands.Cog.listener()
    async def on_ready(self):
        print("Mafia cog is ready")

    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.channel.id in self.mafia_inprosses:
            return
        if message.channel.name == "mafia" and message.channel.id not in self.mafia_channels.keys():
            self.mafia_channels[message.channel.id] = {'current_night': 1, 'players': {}}
        
        if message.channel.id in self.mafia_channels.keys():
            if message.author.id == 511786918783090688 and message.embeds != [] and isinstance(message.embeds[0].title, str):
                new_night = night_pattern.findall(message.embeds[0].title)
                if new_night != []: 
                    self.mafia_channels[message.channel.id]['current_night'] = int(new_night[0])       
                    print("New night: ", self.mafia_channels[message.channel.id]['current_night'])
            
            if message.author.id == 511786918783090688 and message.embeds != [] and isinstance(message.embeds[0].description, str):
                if message.embeds[0].description == "Thank you all for playing! Deleting this channel in 10 seconds":
                    self.bot.dispatch("mafia_ends", self.mafia_channels[message.channel.id], message.channel)
                    return
            if message.author.bot:
                return
            if message.author.id not in self.mafia_channels[message.channel.id]['players'].keys():
                self.mafia_channels[message.channel.id]['players'][message.author.id] = {}
            if self.mafia_channels[message.channel.id]['current_night'] not in self.mafia_channels[message.channel.id]['players'][message.author.id].keys():
                self.mafia_channels[message.channel.id]['players'][message.author.id][self.mafia_channels[message.channel.id]['current_night']] = 1
            else:
                self.mafia_channels[message.channel.id]['players'][message.author.id][self.mafia_channels[message.channel.id]['current_night']] += 1


    @commands.Cog.listener()
    async def on_mafia_ends(self, data: dict, channel: discord.TextChannel):
        self.mafia_inprosses.append(channel.id)
        embed = discord.Embed(title="Scraped Data", description="Data scraped from the channel\n", color=self.bot.default_color)
        for player in data['players'].keys():
            message_record = ""
            for night in data['players'][player].keys():
                message_record += f"Night {night}: {data['players'][player][night]}\n"
            user = channel.guild.get_member(int(player))
            embed.add_field(name=f"{user.name}", value=message_record)
        channel = self.bot.get_channel(824614406410993725)
        await channel.send(embed=embed)
    
    @app_commands.command(name="scrap", description="Scrap a channel for mafia game data")
    async def scrap(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.send_message("Scraping channel...")
        messages: list[discord.Message] = [message async for message in channel.history(limit=None, oldest_first=True)]
        data = {}
        current_night = 1
        for message in messages:
            if message.author.id == 511786918783090688 and message.embeds != [] and isinstance(message.embeds[0].title, str):
                    new_night = night_pattern.findall(message.embeds[0].title)
                    if new_night != []: 
                        current_night = int(new_night[0])       
                        print("New night: ", current_night)
            
            if message.author.bot:
                continue
            if message.author.id not in data.keys():
                data[message.author.id] = {}
            if current_night not in data[message.author.id].keys():
                data[message.author.id][current_night] = 1
            else:
                data[message.author.id][current_night] += 1

        embed = discord.Embed(title="Scraped Data", description="Data scraped from the channel\n", color=self.bot.default_color)
        for player in data.keys():
            message_record = ""
            for night in data[player].keys():
                message_record += f"Night {night}: {data[player][night]}\n"
            user = interaction.guild.get_member(int(player))
            embed.add_field(name=f"{user.name}", value=message_record)

        await interaction.edit_original_response(content=None, embed=embed)
    
    @app_commands.command(name="debug", description="Scrap all mafia channels")
    async def _debug(self, interaction: discord.Interaction):
        await interaction.response.send_message(self.mafia_channels)

    @app_commands.command(name="get_stats", description="Get stats for a user")
    async def _stats(self, interaction: discord.Interaction, message_id: str):
        message_id = int(message_id)
        try:
            message: discord.Message = await interaction.channel.fetch_message(message_id)
        except discord.NotFound:
            await interaction.response.send_message("Message not found")
            return
        await interaction.response.send_message("Scraping message...")
        
        embed: discord.Embed = message.embeds[0]
        currently_alive = []
        currently_dead = []
        for field in embed.fields:
            if "alive" in field.name.lower():
                currently_alive = field.value.split("\n")
                
            if "dead" in field.name.lower():
                currently_dead = field.value.split("\n")
        
        await interaction.edit_original_response(content=f"{currently_alive}\n{currently_dead}", embed=None, allowed_mentions=discord.AllowedMentions.none())

async def setup(bot):
    await bot.add_cog(Mafia(bot), guilds=[discord.Object(785839283847954433)])