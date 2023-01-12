import discord
from discord import app_commands, Interaction
from discord.ext import commands


def is_developer(interaction: Interaction) -> bool:
    return interaction.user.id in interaction.client.owner_ids

def is_owner(interaction: Interaction) -> bool:
    return interaction.user.id == interaction.guild.owner_id

def is_admin(interaction: Interaction) -> bool:
    return interaction.user.guild_permissions.administrator

def can_ban(interaction: Interaction) -> bool:
    return interaction.user.guild_permissions.ban_members

def is_dev():
    def is_developer(ctx):
        return ctx.author.id in ctx.bot.owner_ids
    return commands.check(is_developer)
