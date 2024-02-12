import discord 
import re
from discord import app_commands
from discord.ext import commands
from utils.db import Document
from io import BytesIO
from typing import TypedDict, List, Dict

night_pattern = re.compile(r"Night ([1-9]|1[0-5])")


class NightData(TypedDict):
    NightNumber: int
    Players: Dict[discord.Member, int]

class PlayerData(TypedDict):
    user: discord.Member
    alive: bool
    death_night: int

class MafiaData(TypedDict):
    current_night: int
    players: Dict[int, PlayerData]
    MininumMessages: int
    Nights: Dict[int, NightData]

class Mafia(commands.GroupCog):
    def __init__(self, bot):
        self.bot = bot
        self.mafia_channels: Dict[int, MafiaData] = {}
        self.mafia_inprosses: List[int] = []
        self.db = Document(self.bot.db, "mafia")
    
    async def get_dead_plater(self, str):
        pattern = r"<@!?(\d+)>"
        matches = re.findall(pattern, str)
        return [int(match) for match in matches]

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.channel.id in self.mafia_inprosses:
            return
        if not message.guild: return

        if message.channel.name == "mafia" and message.channel.id not in self.mafia_channels.keys():
            new_game_data: MafiaData = {
                "current_night": 1,
                "players": {},
                "MininumMessages": 3,
                "Nights": {1: {
                    "NightNumber": 1,
                    "Players": {}
                }}
            }
            for member in message.channel.overwrites:
                if isinstance(member, discord.Member):
                    if not member.bot:
                        new_game_data['players'][member.id] = {
                            "user": member,
                            "alive": True,
                            "death_night": 0
                        }
                        new_game_data['Nights'][1]['Players'][member.id] = 0
            self.mafia_channels[message.channel.id] = new_game_data
        
        if message.channel.id in self.mafia_channels.keys():
            if message.author.id == 511786918783090688 and message.embeds != [] and isinstance(message.embeds[0].title, str):
                new_night = night_pattern.findall(message.embeds[0].title)
                if new_night != []: 
                    self.mafia_channels[message.channel.id]['current_night'] = int(new_night[0])
                    self.mafia_channels[message.channel.id]['Nights'][int(new_night[0])]: NightData = {
                        "NightNumber": int(new_night[0]),
                        "Players": {}
                    }

            if message.author.id == 511786918783090688 and message.embeds != [] and isinstance(message.embeds[0].description, str):
                if message.embeds[0].description == "Thank you all for playing! Deleting this channel in 10 seconds":
                    self.bot.dispatch("mafia_ends", self.mafia_channels[message.channel.id], message.channel)
                    return
            
                if message.embeds[0].title == "Currently ded:":
                    dead_players = await self.get_dead_plater(message.embeds[0].description)
                    for player in dead_players:
                        if self.mafia_channels[message.channel.id]['players'][player]['alive']:
                            self.mafia_channels[message.channel.id]['players'][player]['alive'] = False
                            self.mafia_channels[message.channel.id]['players'][player]['death_night'] = self.mafia_channels[message.channel.id]['current_night']

            if message.author.bot: return
            
            if message.author.id not in self.mafia_channels[message.channel.id]['players'].keys():
                pass
            if message.author.id not in self.mafia_channels[message.channel.id]['Nights'][self.mafia_channels[message.channel.id]['current_night']]['Players'].keys():
                self.mafia_channels[message.channel.id]['Nights'][self.mafia_channels[message.channel.id]['current_night']]['Players'][message.author.id] = 1
            else:
                self.mafia_channels[message.channel.id]['Nights'][self.mafia_channels[message.channel.id]['current_night']]['Players'][message.author.id] += 1


    @commands.Cog.listener()
    async def on_mafia_ends(self, data: MafiaData, channel: discord.TextChannel):
        self.mafia_inprosses.append(channel.id)
        log_channel = channel.guild.get_channel(1096669152447582318)

        embed = discord.Embed(description="", color=self.bot.default_color)
        for night in data['Nights'].keys():
            if len(data['Nights'][night]['Players'].keys()) == 0:
                continue
            _str = f"## Night {night}\n"
            for index, player in enumerate(data['Nights'][night]['Players'].keys()):
                user = channel.guild.get_member(int(player))
                if index+1 == len(data['Nights'][night]['Players'].keys()):
                    emoji = "<:nat_reply:1146498277068517386>" 
                else:
                    emoji = "<:nat_replycont:1146496789361479741>"

                _str += f"{emoji} {user.mention}: Sent {data['Nights'][night]['Players'][player]}/{data['MininumMessages']}"
                if data['Nights'][night]['Players'][player] >= data['MininumMessages']:
                    _str += " <:tgk_active:1082676793342951475>\n"
                else:
                    _str += " <:tgk_deactivated:1082676877468119110>\n"
            
            if len(embed.description) + len(_str) > 4096:
                await log_channel.send(embed=embed)
                embed = discord.Embed(description="", color=self.bot.default_color)
            else:
                embed.description += _str

        await log_channel.send(embed=embed)

        dead_players_info = ""
        embed = discord.Embed(title="", description="", color=self.bot.default_color)
        for i in data['players'].keys():
            if not data['players'][i]['alive']:
                dead_players_info += f"{data['players'][i]['user'].mention} died on night {data['players'][i]['death_night']}\n"
        embed.add_field(name="Dead Players", value=dead_players_info)
    
    @app_commands.command(name="scrap", description="Scrap a channel for mafia game data")
    async def scrap(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.send_message("Scraping channel...")
        messages: list[discord.Message] = [message async for message in channel.history(limit=None, oldest_first=True)]
        data: MafiaData = {
            "current_night": 1,
            "players": {},
            "MininumMessages": 3,
            "Nights": {1: {
                "NightNumber": 1,
                "Players": {}
            }}
        }
        players = await self.get_dead_plater(messages[0].content)
        for player in players:
            data['players'][player]: PlayerData = {
                "user": channel.guild.get_member(player),
                "alive": True,
                "death_night": None
            }

        current_night = 1
        for message in messages:
            if message.author.id == 511786918783090688 and message.embeds != [] and isinstance(message.embeds[0].title, str):
                new_night = night_pattern.findall(message.embeds[0].title)
                if new_night != []: 
                    current_night = int(new_night[0])
                    data['current_night'] = current_night
                    data['Nights'][current_night]: NightData = {
                        "NightNumber": current_night,
                        "Players": {}
                    }
                
                if len(message.embeds) > 0:
                    if message.embeds[0].title == "Currently ded:":
                        dead_players = await self.get_dead_plater(message.embeds[0].description)
                        for player in dead_players:
                            if data['players'][player]['alive']:
                                data['players'][player]['alive'] = False
                                data['players'][player]['death_night'] = current_night

            if message.author.bot:
                continue
            if message.author.id not in data['players'].keys():
                continue
            if message.author.id not in data['Nights'][current_night]['Players'].keys():
                data['Nights'][current_night]['Players'][message.author.id] = 1                
            else:
                data['Nights'][current_night]['Players'][message.author.id] += 1
        
        embed = discord.Embed(title="Scraped Data", description="", color=self.bot.default_color)
        for night in data['Nights'].keys():
            _str = f"## Night {night}\n"

            for index, player in enumerate(data['Nights'][night]['Players'].keys()):
                user = channel.guild.get_member(int(player))
                if index+1 == len(data['Nights'][night]['Players'].keys()):
                    emoji = "<:nat_reply:1146498277068517386>"
                else:
                    emoji = "<:nat_replycont:1146496789361479741>"

                _str += f"{emoji} {user.mention}: {data['Nights'][night]['Players'][player]}/{data['MininumMessages']}"
                if data['Nights'][night]['Players'][player] >= data['MininumMessages']:
                    _str += " <:tgk_active:1082676793342951475>\n"
                else:
                    _str += " <:tgk_deactivated:1082676877468119110>\n"
            print(len(_str))
            print('----')
            embed.description += _str

        dead_players_info = ""
        for i in data['players'].keys():
            if not data['players'][i]['alive']:
                dead_players_info += f"{data['players'][i]['user'].mention} died on night {data['players'][i]['death_night']}\n"
        embed.add_field(name="Dead Players", value=dead_players_info)

        await interaction.edit_original_response(content=None, embed=embed, allowed_mentions=discord.AllowedMentions.none())
        data['_id'] = channel.id
        ## make a .json file of the data using BytesIO
        buffer = BytesIO()
        buffer.write(str(data).encode('utf-8'))
        buffer.seek(0)
        await interaction.channel.send(file=discord.File(buffer, filename=f"MAFIA DATA DUMP.json"))

    @scrap.error
    async def scrap_error(self, interaction: discord.Interaction, error):
        await interaction.followup.send(f"An error occured: {error}")
    
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

