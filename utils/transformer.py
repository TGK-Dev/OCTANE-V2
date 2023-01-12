import discord
import re
from discord import app_commands, Interaction
from discord.ext import commands


time_regex = re.compile("(?:(\d{1,5})(h|s|m|d))+?")
time_dict = {"h": 3600, "s": 1, "m": 60, "d": 86400}

class MutipleRole(app_commands.Transformer):
    async def transform(self, interaction: Interaction, value: str,):
        value = value.split(" ")
        roles = [await commands.RoleConverter().convert(interaction, role) for role in value]
        return roles

class MutipleUser(app_commands.Transformer):
    async def transform(self, interaction: Interaction, value: str,):
        value = value.split(" ")
        users = [await commands.UserConverter().convert(interaction, user) for user in value]
        return users

class MutipleMember(app_commands.Transformer):
    async def transform(self, interaction: Interaction, value: str,):
        value = value.split(" ")
        members = [await commands.MemberConverter().convert(interaction, member) for member in value]
        return members

class TimeConverter(app_commands.Transformer):
    async def transform(self, interaction: Interaction, value: str,):
        args = value.lower()
        matches = re.findall(time_regex, args)
        time = 0
        for key, value in matches:
            try:
                time += time_dict[value] * float(key)
            except KeyError:
                return await interaction.response.send_message(f"{value} is an invalid time key! h|m|s|d are valid arguments", ephemeral=True)                
            except ValueError:
                return await interaction.response.send_message(f"{key} is not a number!", ephemeral=True)
        return round(time)
