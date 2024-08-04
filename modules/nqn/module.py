import discord
import aiohttp
import difflib
from typing import TypedDict
from discord import Interaction, app_commands
from discord.ext import commands
from utils.converters import chunk
from utils.paginator import Paginator
from utils.db import Document


class Emoji(TypedDict):
    id: int
    name: str
    roles: list
    require_colons: bool
    managed: bool
    animated: bool

class nqn(commands.GroupCog, name="pemoji"):
    def __init__(self, bot):
        self.bot = bot
        self.config = Document(bot.db, "nqn")
        self.config_cache = {}
        self.emoijs = {}
        self.webhooks = {}
        self.whitelist = [651711446081601545, 488614633670967307, 301657045248114690]

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id not in self.whitelist:
            await interaction.response.send_message(
                "You are not authorized to use this command.", ephemeral=True
            )
            return False
        return True

    @commands.Cog.listener()
    async def on_ready(self):
        configs = await self.config.get_all()
        for config in configs:
            self.config_cache[config["_id"]] = config

        async with aiohttp.ClientSession() as session:
            url = f"https://discord.com/api/v10/applications/{self.bot.user.id}/emojis"
            headers = {
                "Authorization": f"Bot {self.bot.http.token}",
                "Content-Type": "application/json",
            }
            async with session.get(url, headers=headers) as response:
                emojis = await response.json()
                emojis: list[Emoji] = emojis["items"]
            await session.close()

        if response.status != 200:
            return
        for emoji in emojis:
            if emoji["name"] not in self.emoijs.keys():
                if emoji["animated"]:
                    self.emoijs[emoji["name"]] = f"<a:{emoji['name']}:{emoji['id']}>"
                else:
                    self.emoijs[emoji["name"]] = f"<:{emoji['name']}:{emoji['id']}>"

        print(f"Loaded {len(self.emoijs)} emojis")

    async def find_most_similar(self, target):
        return max(
            list(self.emoijs.keys()),
            key=lambda s: difflib.SequenceMatcher(None, target, s).ratio(),
            default=None,
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.author.id not in self.whitelist:
            return
        if message.author.premium_since is None:
            return
        if message.author.id in self.config_cache.keys():
            if not self.config_cache[message.author.id]["enabled"]:
                return
        else:
            data = await self.config.find(message.author.id)
            if data is None:
                data = {"_id": message.author.id, "enabled": False}
                await self.config.insert(data)
                self.config_cache[message.author.id] = data
            else:
                self.config_cache[message.author.id] = data
                if not data["enabled"]:
                    return

        message_conent = message.content
        replace = False
        for word in message_conent.split():
            if not word.startswith(":"):
                continue

            matched_emoji = await self.find_most_similar(word)
            if matched_emoji is None:
                continue
            else:
                message_conent = message_conent.replace(
                    word, self.emoijs[matched_emoji]
                )
                if not replace:
                    replace = True

        if not replace:
            return

        if message.channel.id not in self.webhooks.keys():
            webhooks = await message.channel.webhooks()
            for webhook in webhooks:
                if webhook.user.id == self.bot.user.id:
                    self.webhooks[message.channel.id] = webhook
                    break
            else:
                avatar = await self.bot.user.avatar.read()
                webhook = await message.channel.create_webhook(
                    name="NQN", avatar=avatar
                )
                self.webhooks[message.channel.id] = webhook

        webhook: discord.Webhook = self.webhooks[message.channel.id]
        kewargs = {
            "content": message_conent,
            "username": message.author.display_name,
            "avatar_url": message.author.avatar.url,
            "allowed_mentions": discord.AllowedMentions(
                users=True, everyone=False, roles=False, replied_user=True
            ),
        }
        await webhook.send(**kewargs)
        await message.delete()

    @app_commands.command(name="list", description="List all NQN")
    async def _list_nqn(self, interaction: Interaction, hidden: bool = False):
        emoji_chunked = chunk(self.emoijs.keys(), 10)
        pages = []
        for chunked in emoji_chunked:
            embed = discord.Embed(
                title="NQN List", color=interaction.client.default_color, description=""
            )
            for emoji in chunked:
                embed.description += f"{emoji}: {self.emoijs[emoji]}\n"
            pages.append(embed)

        await Paginator(interaction, pages).start(
            embeded=True, timeout=60, quick_navigation=False, hidden=hidden
        )

    async def upload(self, emoji: discord.Emoji):
        emoji_data = await emoji.read()
        data = discord.utils._bytes_to_base64_data(emoji_data)
        if emoji.animated:
            data += f"data:image/gif;base64,{emoji_data}"
        else:
            data += f"data:image/png;base64,{emoji_data}"
        async with aiohttp.ClientSession() as session:
            url = f"https://discord.com/api/v10/applications/{self.bot.user.id}/emojis"
            headers = {
                "Authorization": f"Bot {self.bot.http.token}",
                "Content-Type": "application/json",
            }
            json = {"name": emoji.name, "image": data}
            async with session.post(url, headers=headers, json=json) as response:
                emoji = await response.json()
                if "available" in emoji.keys():
                    if emoji["animated"]:
                        self.emoijs[emoji["name"]] = (
                            f"<a:{emoji['name']}:{emoji['id']}>"
                        )
                    else:
                        self.emoijs[emoji["name"]] = f"<:{emoji['name']}:{emoji['id']}>"
                    await session.close()
                    return True

    @app_commands.command(name="add-guild", description="Add NQN to guild")
    async def add_guild(self, interaction: Interaction):
        await interaction.response.send_message("Adding NQN to guild")
        added_emojis = 0
        failed = 0
        for emoji in interaction.guild.emojis:
            if emoji.name in self.emoijs.keys():
                continue
            else:
                added = await self.upload(emoji)
                if added:
                    added_emojis += 1
                else:
                    failed += 1

        await interaction.edit_original_response(
            content=f"Added {added_emojis} emojis and failed to add {failed} emojis"
        )

    @app_commands.command(name="toggle", description="Toggle NQN")
    async def toggle(self, interaction: Interaction):
        data = self.config_cache.get(interaction.user.id)
        if data is None:
            data = {"_id": interaction.user.id, "enabled": False}
            await self.config.insert(data)
            self.config_cache[interaction.user.id] = data
        else:
            data["enabled"] = not data["enabled"]
            await self.config.update(data)
            self.config_cache[interaction.user.id] = data

        await interaction.response.send_message(
            f"{'Enabled' if data['enabled'] else 'Disabled'} NQN"
        )


async def setup(bot):
    await bot.add_cog(nqn(bot))
