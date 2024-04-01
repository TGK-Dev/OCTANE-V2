import io
import os
import re
import zlib
import logging

import aiohttp
import discord
from discord.ext import commands
from utils.checks import is_dev
from discord import Interaction, app_commands

class SphinxObjectFileReader:
   
    BUFSIZE = 16 * 1024

    def __init__(self, buffer):
        self.stream = io.BytesIO(buffer)

    def readline(self):
        return self.stream.readline().decode("utf-8")

    def skipline(self):
        self.stream.readline()

    def read_compressed_chunks(self):
        decompressor = zlib.decompressobj()
        while True:
            chunk = self.stream.read(self.BUFSIZE)
            if len(chunk) == 0:
                break
            yield decompressor.decompress(chunk)
        yield decompressor.flush()

    def read_compressed_lines(self):
        buf = b""
        for chunk in self.read_compressed_chunks():
            buf += chunk
            pos = buf.find(b"\n")
            while pos != -1:
                yield buf[:pos].decode("utf-8")
                buf = buf[pos + 1 :]
                pos = buf.find(b"\n")

class Docs(commands.Cog, name="Documentation"):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)

        self.page_types = {
            "discord.py": "https://discordpy.readthedocs.io/en/latest/",
            "levelling": "https://discord-ext-levelling.readthedocs.io/en/latest/",
        }

    def finder(self, text, collection, *, key=None, lazy=True):
        suggestions = []
        text = str(text)
        pat = ".*?".join(map(re.escape, text))
        regex = re.compile(pat, flags=re.IGNORECASE)
        for item in collection:
            to_search = key(item) if key else item
            r = regex.search(to_search)
            if r:
                suggestions.append((len(r.group()), r.start(), item))

        def sort_key(tup):
            if key:
                return tup[0], tup[1], key(tup[2])
            return tup

        if lazy:
            return (z for _, _, z in sorted(suggestions, key=sort_key))
        else:
            return [z for _, _, z in sorted(suggestions, key=sort_key)]

    def parse_object_inv(self, stream, url):
    
        result = {}

     
        inv_version = stream.readline().rstrip()

        if inv_version != "# Sphinx inventory version 2":
            raise RuntimeError("Invalid objects.inv file version.")

        stream.readline().rstrip()[11:]
        stream.readline().rstrip()[11:]


        line = stream.readline()
        if "zlib" not in line:
            raise RuntimeError("Invalid objects.inv file, not z-lib compatible.")

        # This code mostly comes from the Sphinx repository.
        entry_regex = re.compile(r"(?x)(.+?)\s+(\S*:\S*)\s+(-?\d+)\s+(\S+)\s+(.*)")
        for line in stream.read_compressed_lines():
            match = entry_regex.match(line.rstrip())
            if not match:
                continue

            name, directive, prio, location, dispname = match.groups()
            domain, _, subdirective = directive.partition(":")
            if directive == "py:module" and name in result:

                continue

            if directive == "std:doc":
                subdirective = "label"

            if location.endswith("$"):
                location = location[:-1] + name

            key = name if dispname == "-" else dispname
            prefix = f"{subdirective}:" if domain == "std" else ""

            result[f"{prefix}{key}"] = os.path.join(url, location)

        return result

    async def build_rtfm_lookup_table(self, page_types):
        cache = {}
        for key, page in page_types.items():
            async with aiohttp.ClientSession() as session:
                async with session.get(page + "/objects.inv") as resp:
                    if resp.status != 200:
                        raise RuntimeError(
                            "Cannot build rtfm lookup table, try again later."
                        )

                    stream = SphinxObjectFileReader(await resp.read())
                    cache[key] = self.parse_object_inv(stream, page)

        self._rtfm_cache = cache

    async def do_rtfm(self, interaction: Interaction, key, obj):
        page_types = self.page_types

        if obj is None:
            await interaction.followup.send("You need to pass an object to search for.")
            return

        if not hasattr(self, "_rtfm_cache"):
            await self.build_rtfm_lookup_table(page_types)

        cache = list(self._rtfm_cache[key].items())

        self.matches = self.finder(obj, cache, key=lambda t: t[0], lazy=False)[:8]

        e = discord.Embed(colour=0x2b2d31)
        e.set_footer(text=f'Requested By {interaction.user}')
        if len(self.matches) == 0:
            return await interaction.followup.send('Could not find anything. Sorry!')

        e.description = "\n".join(f"[`{key}`]({url})" for key, url in self.matches)
        await interaction.followup.send(embed=e)
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id != 270904126974590976: return
        if len(message.embeds) == 0: return
        if message.embeds[0].title != "Now Playing": return
        await message.author.move_to(None)

    @app_commands.command(name='docs', description='Gives you a documentation link for a d.py entity.')
    @app_commands.describe(query='The entity to search for.', key='The documentation to search in. (Optional)')
    @app_commands.check(is_dev)
    async def rtfm(self, interaction: Interaction, query: str, key: str = None):
        await interaction.response.defer(thinking=True)
        key = key or ""
        query = key + query
        key = "discord.py"

        if query is not None:
            if query.lower() == "rtfm":
                await interaction.followup.send(
                    embed=discord.Embed.from_dict(
                        {
                            "title": "Read The Fucking Manual",
                            "color": "0x00FC7E",
                            "description": "You expect me to know?",
                            "footer": {"text": "Imagine including easter eggs"},
                        }
                    )
                )

        await self.do_rtfm(interaction, key, query)


async def setup(bot):
    await bot.add_cog(Docs(bot))