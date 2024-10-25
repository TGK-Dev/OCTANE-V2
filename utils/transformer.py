import discord
from discord import app_commands, Interaction
from discord.ext import commands
import re

time_regex = re.compile(r"(?:(\d{1,5})(h|s|m|d))+?")
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
                time += time_dict[k] * float(v)
            except KeyError:
                raise KeyError
            except ValueError:
                raise ValueError
        return time


class DMCConverter(app_commands.Transformer):
    async def transform(self, interaction: Interaction, value: str):
        value = value.lower()
        value = (
            value.replace("⏣", "")
            .replace(",", "")
            .replace("k", "e3")
            .replace("m", "e6")
            .replace(" mil", "e6")
            .replace("mil", "e6")
            .replace("b", "e9")
        )
        if "e" not in value:
            return int(value)
        value = value.split("e")

        if len(value) > 2:
            raise Exception(f"Invalid number format try using 1e3 or 1k: {value}")

        price = value[0]
        multi = int(value[1])
        price = float(price) * (10**multi)

        return int(price)


class MutipleRole(app_commands.Transformer):
    async def transform(
        self,
        interaction: Interaction,
        value: str,
    ):
        value = value.split(" ")
        roles = [
            await commands.RoleConverter().convert(interaction, role) for role in value
        ]
        return roles


class MultipleMember(app_commands.Transformer):
    async def transform(
        self,
        interaction: Interaction,
        value: str,
    ):
        value = value.split(" ")
        value = [
            value.replace("<", "").replace(">", "").replace("@", "").replace("!", "")
            for value in value
        ]
        members = []
        for i in value:
            if i not in ["", " ", None, "None"]:
                member = interaction.guild.get_member(int(i))
                if member is not None:
                    members.append(member)

        return members


class MutipleChannel(app_commands.Transformer):
    async def transform(
        self,
        interaction: Interaction,
        value: str,
    ):
        value = value.split(" ")
        value = [
            value.replace("<", "").replace(">", "").replace("#", "") for value in value
        ]
        channels = [
            interaction.guild.get_channel(int(channel))
            for channel in value
            if channel is not None
        ]
        return channels
