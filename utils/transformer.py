import discord
from discord import app_commands, Interaction
from discord.ext import commands
import re

time_regex = re.compile("(?:(\d{1,5})(h|s|m|d))+?")
time_dict = {"h": 3600, "s": 1, "m": 60, "d": 86400}

class TimeConverter(app_commands.Transformer):
    async def transform(self, interaction: discord.Interaction, argument: str) -> int:
        matches = time_regex.findall(argument.lower())
        if len(matches) == 0:
            try:
                return int(argument)
            except Exception as e:
                raise e
        time = 0
        for v, k in matches:
            try:
                time += time_dict[k]*float(v)
            except KeyError:
                raise KeyError
            except ValueError:
                raise ValueError
        return time

class MutipleRole(app_commands.Transformer):
    async def transform(self, interaction: Interaction, value: str,):
        value = value.split(" ")
        roles = [await commands.RoleConverter().convert(interaction, role) for role in value]
        return roles

class MultipleMember(app_commands.Transformer):
    async def transform(self, interaction: Interaction, value: str,):
        value = value.split(" ")
        value = [value.replace("<", "").replace(">", "").replace("@", "").replace("!", "") for value in value]
        members = [interaction.guild.get_member(int(member)) for member in value if member is not None]
        return members

class MutipleChannel(app_commands.Transformer):
    async def transform(self, interaction: Interaction, value: str,):
        value = value.split(" ")
        value = [value.replace("<", "").replace(">", "").replace("#", "") for value in value]
        channels = [interaction.guild.get_channel(int(channel)) for channel in value if channel is not None]
        return channels