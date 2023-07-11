import discord
from discord.ext import commands
from discord import app_commands
from utils.db import Document
from typing import List
import datetime
from utils.checks import is_dev
import asyncio

class Dank_Events(commands.GroupCog, name="dank"):
    def __init__(self, bot):
        self.bot = bot
        self.bot.dank_db = self.bot.mongo["Dank_Data"]
        self.bot.dank_items = Document(self.bot.dank_db, "Item prices")
        self.bot.dank_items_cache = {}
    
    async def item_autocomplete(self, interaction: discord.Interaction, string: str) -> List[app_commands.Choice[str]]:
        choices = []
        for item in self.bot.dank_items_cache.keys():
            if string.lower() in item.lower():
                choices.append(app_commands.Choice(name=item, value=item))
        if len(choices) == 0:
            return [
                app_commands.Choice(name=item, value=item)
                for item in self.bot.dank_items_cache.keys()
            ]
        else:
            return choices[:24]


    @commands.Cog.listener()
    async def on_ready(self):
        for items in await self.bot.dank_items.get_all():
            self.bot.dank_items_cache[items["_id"]] = items
    
    item = app_commands.Group(name="item", description="Some commands related to items")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild is None: return

        if message.channel.id == 1079670945171640360:
            return self.bot.dispatch("dank_price_update", message)

        if message.interaction is not None:
            if message.interaction.name == "item" and message.guild.id == 947525009247707157:
                return self.bot.dispatch("dank_price_update_from_cmd", message)

    
    @commands.Cog.listener()
    async def on_dank_price_update_from_cmd(self, message: discord.Message):
        if len(message.embeds) == 0: return

        embed = message.embeds[0]
        item = embed.title
        price = int(message.embeds[0].fields[0].value.split("\n")[0].split(" ")[-1].replace(",", ""))

        data = await self.bot.dank_items.find(item)
        if not data:
            data = {"_id": item, "price": price, 'last_updated': datetime.datetime.now(), 'last_prices': []}
            await self.bot.dank_items.insert(data)
        else:
            old_price = data['price']
            update_data = {"day": data['last_updated'].strftime("%d/%m/%Y"),"old_price": old_price, "new_price": price}
            data['last_prices'].append(update_data)
            data['price'] = price
            data['last_updated'] = datetime.datetime.now()
            if len(data['last_prices']) > 10:
                data['last_prices'].pop(0)
            await self.bot.dank_items.update(data)
        
        await message.add_reaction("<:YES_TICK:957348921120792717>")
        await asyncio.sleep(2.5)
        await message.remove_reaction("<:YES_TICK:957348921120792717>", self.bot.user)

    @commands.Cog.listener()
    async def on_dank_price_update(self, message: discord.Message):

        if len(message.embeds) <= 0:
            return

        embed = message.embeds[0]
        item = embed.title
        price = embed.fields[1].value.replace("`","").replace("⏣","").replace(",", "").replace(" ","")
        price = int(price)

        data = await self.bot.dank_items.find(item)
        if not data:
            data = {"_id": item, "price": price, 'last_updated': datetime.datetime.now(), 'last_prices': []}
            await self.bot.dank_items.insert(data)
        else:
            old_price = data['price']
            if old_price == price: return
            update_data = {"day": data['last_updated'].strftime("%d/%m/%Y"),"old_price": old_price, "new_price": price}
            data['last_prices'].append(update_data)            
            data['price'] = price
            if len(data['last_prices']) > 10:
                data['last_prices'].pop(0)
            data['last_updated'] = datetime.datetime.now()
            await self.bot.dank_items.update(data)
        
        await message.add_reaction("<:YES_TICK:957348921120792717>")
    
    @item.command(name="stats", description="Get the stats of an item")
    @app_commands.autocomplete(item=item_autocomplete)
    @app_commands.describe(item="The item to get the stats of")
    async def item_stats(self, interaction: discord.Interaction, item: str):
        item = await self.bot.dank_items.find(item)
        if not item: return await interaction.response.send_message("Item not found", ephemeral=True)
        embed = discord.Embed(title=item["_id"], color=interaction.client.default_color, description="")
        embed.description += f"**Price:** `⏣ {item['price']:,}`\n"
        embed.description += f"**Last Updated:** <t:{round(item['last_updated'].timestamp())}:R> | `{item['last_updated'].strftime('%d/%m/%Y %H:%M:%S')}`\n"
        embed.description += f"**Price History:**\n"
        price_history = "```diff\n"
        if len(item['last_prices']) == 0:
            price_history += "No price history found\n"
        else:
            for index,price in enumerate(item['last_prices']):
                history = f"⏣ {price['old_price']} -> ⏣ {price['new_price']}"
                if price['new_price'] > price['old_price']:
                    price_history += f"+ {history}\n"
                else:
                    price_history += f"- {history}\n"
        price_history += "\n```"
        embed.description += price_history
        await interaction.response.send_message(embed=embed)
    
    @item.command(name="update", description="Update an items price")
    @app_commands.autocomplete(item=item_autocomplete)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(item="The item to update the price of", price="The new price of the item")
    async def item_update(self, interaction: discord.Interaction, item: str, price: int):
        item = await self.bot.dank_items.find(item)
        if not item:
            item = {"_id": item, "price": price, 'last_updated': datetime.datetime.now(), 'last_prices': []}
            await self.bot.dank_items.insert(item)
            self.bot.dank_items_cache[item["_id"]] = item
            embed = discord.Embed(description=f"Added `{item['_id']}` with price `⏣ {price}`", color=interaction.client.default_color)
        else:
            old_price = item['price']
            update_data = {"day": item['last_updated'].strftime("%d/%m/%Y"),"old_price": old_price, "new_price": price}
            item['last_prices'].append(update_data)
            item['price'] = price
            if len(item['last_prices']) > 10:
                item['last_prices'].pop(0)
            item['last_updated'] = datetime.datetime.now()
            await self.bot.dank_items.update(item)
            self.bot.dank_items_cache[item["_id"]] = item
        embed = discord.Embed(description=f"Updated `{item['_id']}` from `⏣ {old_price}` to `⏣ {price}`", color=interaction.client.default_color)
        await interaction.response.send_message(embed=embed)

    @item.command(name="delete", description="Delete an item")
    @app_commands.autocomplete(item=item_autocomplete)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(item="The item to delete")
    async def item_delete(self, interaction: discord.Interaction, item: str):
        item = await self.bot.dank_items.find(item)
        if not item: return await interaction.response.send_message("Item not found", ephemeral=True)
        await self.bot.dank_items.delete(item)
        try:
            del self.bot.dank_items_cache[item["_id"]]
        except KeyError:
            pass
        await interaction.response.send_message("Item deleted successfully", ephemeral=True)    
    
    @item.command(name="bulk_update", description="Bulk update items")
    @app_commands.describe(message="The message to bulk update items from")
    @app_commands.check(is_dev)
    async def item_force_scrape(self, interaction: discord.Interaction, message: str):
        await interaction.response.send_message("Scraping...", ephemeral=True)
        try:
            message = await interaction.channel.fetch_message(message)
        except discord.NotFound:
            return await interaction.edit_original_response("Message not found")
        
        await interaction.edit_original_response(embed=discord.Embed(description="Message Found starting scrape...", color=interaction.client.default_color), content=None)
        embed = message.embeds[0]
        items = embed.description.replace("*", "").replace("`", "").replace("⏣", "").replace(",", "").split("\n")

        success = ""
        failed = ""
        same = ""

        for item in items:
            raw = item.removeprefix(" ").split(":")
            item = raw[0].removesuffix(" ")
            try:
                price = int(raw[1].removeprefix(" "))
            except:
                failed += f"{item}: {raw[1]}\n"
                continue
            data = await self.bot.dank_items.find(item)
            if not data:
                data = {"_id": item, "price": price, 'last_updated': datetime.datetime.now(), 'last_prices': []}
                await self.bot.dank_items.insert(data)
                success += f"{item}: {data['price']}\n"
            else:
                if data['price'] == price: 
                    same += f"{item}: {data['price']}\n"
                    continue
                old_price = data['price']
                update_data = {"day": data['last_updated'].strftime("%d/%m/%Y"),"old_price": old_price, "new_price": price}
                data['last_prices'].append(update_data)
                data['price'] = price
                if len(data['last_prices']) > 10:
                    data['last_prices'].pop(0)
                data['last_updated'] = datetime.datetime.now()
                await self.bot.dank_items.update(data)
                success += f"{item}: {old_price} -> {data['price']}" + "📉\n" if old_price > price else "📈\n"
        
        final_embed = discord.Embed(title="Scrape Complete", color=interaction.client.default_color, description="")
        final_embed.description += f"**### Success:**\n{success}"
        final_embed.description += f"**### Failed:**\n{failed}"
        final_embed.description += f"**### Same:**\n{same}"
        await interaction.edit_original_response(embed=final_embed, content=None)


async def setup(bot):
    await bot.add_cog(Dank_Events(bot), guilds=[discord.Object(999551299286732871), discord.Object(785839283847954433), discord.Object(947525009247707157)])