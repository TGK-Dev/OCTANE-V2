from discord import app_commands, Interaction


def is_developer(interaction: Interaction) -> bool:
    return interaction.user.id in interaction.client.owner_ids


def is_owner(interaction: Interaction) -> bool:
    return interaction.user.id == interaction.guild.owner_id


def is_admin(interaction: Interaction) -> bool:
    return interaction.user.guild_permissions.administrator


def can_ban(interaction: Interaction) -> bool:
    return interaction.user.guild_permissions.ban_members


def is_dev(interaction: Interaction) -> bool:
    return interaction.user.id in interaction.client.owner_ids


class Blocked(app_commands.AppCommandError):
    def __call__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
