
import datetime
import discord
import asyncio
import re

from discord.ext import commands, tasks
from copy import deepcopy
from discord import app_commands
from utils.db import Document
from typing import List
from utils.views.buttons import Confirm
from utils.checks import is_dev

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.vote_remider_task = self.check_vote_reminders.start()
        self.bot.votes = Document(self.bot.db, "votes")
        self.vote_task_progress = False
        self.bot.dank_db = self.bot.mongo["Dank_Data"]
        self.bot.dank_items = Document(self.bot.dank_db, "Item prices")

    def cog_unload(self):
        self.vote_remider_task.cancel()
    
    @tasks.loop(minutes=1)
    async def check_vote_reminders(self):
        if self.vote_task_progress:
            return
        self.vote_task_progress = True

        current_time = datetime.datetime.utcnow()
        current_data = await self.bot.votes.get_all()
        for data in current_data:
            if data["reminded"] == True: continue
        
            expired_time = data['last_vote'] + datetime.timedelta(hours=12)
            if current_time >= expired_time and data["reminded"] == False:
                self.bot.dispatch("vote_reminder", data)
            
            if expired_time > current_time + datetime.timedelta(days=30):
                await self.bot.votes.delete(data['_id'])
        
        self.vote_task_progress = False
    
    @check_vote_reminders.before_loop
    async def before_check_vote_reminders(self):
        await self.bot.wait_until_ready()
    
    @commands.Cog.listener()
    async def on_vote_reminder(self, data):
        if data["reminded"] == True: return

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Vote for TGK at Top.gg", emoji="<a:tgk_icon:1002504426172448828>",url="https://top.gg/servers/785839283847954433/vote"))

        guild = self.bot.get_guild(785839283847954433)
        member = guild.get_member(data['_id'])
        if member is None:
            return await self.bot.votes.delete(data['_id'])

        await member.remove_roles(guild.get_role(786884615192313866))
        data['reminded'] = True
        await self.bot.votes.upsert(data)
        try:
            await member.send("You can now vote for The Gambler's Kingdom again!", view=view)
        except discord.HTTPException:
            pass
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild or message.guild.id != 785839283847954433: return

        if message.channel.id == 1079670945171640360:
            self.bot.dispatch("dank_price_update", message)

        if message.author.id != 270904126974590976: return
        if len(message.embeds) == 0: 
            return
        embed = message.embeds[0]
        if isinstance(embed, discord.Embed) == False: return
        if embed.description is None: return
        if embed.description.startswith("Successfully paid") and embed.description.endswith("from the server's pool!"):
            command_message = await message.channel.fetch_message(message.reference.message_id)
            if command_message.interaction is None: return
            if command_message.interaction.name != "serverevents payout": return

            embed = command_message.embeds[0].to_dict()
            winner = re.findall(r"<@!?\d+>", embed['description'])
            prize = re.findall(r"\*\*(.*?)\*\*", embed['description'])[0]
            emojis = list(set(re.findall(":\w*:\d*", prize)))
            for emoji in emojis :prize = prize.replace(emoji,"",100); prize = prize.replace("<>","",100);prize = prize.replace("<a>","",100);prize = prize.replace("  "," ",100)

            log_embed = discord.Embed(title="Server Events Payout", description=f"",color=self.bot.default_color)
            log_embed.description += f"**Winner**: {winner[0]}\n"
            log_embed.description += f"**Prize**: {prize}\n"
            log_embed.description += f"**Paid by**: {command_message.interaction.user.mention}\n"
            link_view = discord.ui.View()
            link_view.add_item(discord.ui.Button(label="Go to Payout Message", url=command_message.jump_url))
            log_channel = self.bot.get_channel(1076586539368333342)
            await log_channel.send(embed=log_embed, view=link_view)
        elif embed.description.startswith('Successfully donated!') and message.channel.id in [851663580620521472, 812711254790897714, 1051387593318740009]:
            command_message = await message.channel.fetch_message(message.reference.message_id)
            if command_message.interaction is None: return
            if command_message.interaction.name != "serverevents donate": return

            embed = command_message.embeds[0].to_dict()
            donor = command_message.interaction.user
            prize = re.findall(r"\*\*(.*?)\*\*", embed['description'])[0]
            emojis = list(set(re.findall(":\w*:\d*", prize)))
            for emoji in emojis :prize = prize.replace(emoji,"",100); prize = prize.replace("<>","",100);prize = prize.replace("<a>","",100);prize = prize.replace("  "," ",100)

            await command_message.reply(f'{donor.mention} successfully donated **{prize}** to the server pool!', allowed_mentions=discord.AllowedMentions.none())
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return

        elif isinstance(error, commands.CommandOnCooldown):
            return await ctx.send(f"This command is on cooldown for {error.retry_after:.2f} seconds")

        elif isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send(f"Missing required argument {error.param.name}")

        elif isinstance(error, commands.BadArgument):
            return await ctx.send(f"Bad argument {error.param.name}")

        elif isinstance(error, commands.MissingPermissions):
            return await ctx.send(f"You don't have permission to use this command")

        elif isinstance(error, commands.BotMissingPermissions):
            return await ctx.send(f"I don't have permission to use this command")

        elif isinstance(error, commands.CheckFailure):
            return await ctx.send(f"You don't have permission to use this command")

        elif isinstance(error, commands.CommandInvokeError):
            return await ctx.send(f"An error occured while executing this command\n```\n{error}\n```")

        else:
            embed = discord.Embed(color=0xE74C3C,description=f"<:dnd:840490624670892063> | Error: `{error}`")
            await ctx.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_presence_update(self, before, after):
        if before.guild.id != 785839283847954433: return
        supporter_role = before.guild.get_role(992108093271965856)
        supporter_log_channel = before.guild.get_channel(1031514773310930945)
        if len(after.activities) <= 0 and supporter_role in after.roles:
            await after.remove_roles(supporter_role, reason="No longer supporting")
            return        
        await asyncio.sleep(5)

        for activity in after.activities:
            try:
                if activity.type == discord.ActivityType.custom:
                    if ".gg/tgk" in activity.name.lower():

                        if supporter_role in after.roles: return
                        embed = discord.Embed(description=f"Thanks for supporting the The Gambler's Kingdom\n\nYou have been given the {supporter_role.mention} role", color=supporter_role.color)
                        embed.set_author(name=f"{after.name}#{after.discriminator} ({after.id})", icon_url=after.avatar.url if after.avatar else after.default_avatar)
                        embed.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar.url)
                        embed.timestamp = datetime.datetime.now()
                        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/869579480509841428.gif?v=1")
                        await supporter_log_channel.send(embed=embed)
                        await after.add_roles(supporter_role)
                        return

                    elif not ".gg/tgk" in activity.name.lower():
                        
                        if supporter_role in after.roles: await after.remove_roles(supporter_role)                        
                        return
            except Exception as e:
                pass

class Dank_Events(commands.GroupCog, name="dank"):
    def __init__(self, bot):
        self.bot = bot
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
            if message.interaction.name == "item":
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
            data['last_prices'].append(data['price'])
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
        # embed.description += f"**Price History:**\n"
        # price_history = "```diff\n"
        # if len(item['last_prices']) == 0:
        #     price_history += "No price history found\n"
        # else:
        #     for index,price in enumerate(item['last_prices']):
        #         history = f"⏣ {price['old_price']} -> ⏣ {price['new_price']}"
        #         if price['new_price'] > price['old_price']:
        #             price_history += f"+ {history}\n"
        #         else:
        #             price_history += f"- {history}\n"
        # price_history += "\n```"
        # embed.description += price_history
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
                old_price = data['price']
                update_data = {"day": data['last_updated'].strftime("%d/%m/%Y"),"old_price": old_price, "new_price": price}
                data['last_prices'].append(update_data)
                data['price'] = price
                if len(data['last_prices']) > 10:
                    data['last_prices'].pop(0)
                data['last_updated'] = datetime.datetime.now()
                await self.bot.dank_items.update(data)
                success += f"{item}: {data['price']}\n"
        
        final_embed = discord.Embed(title="Scrape Complete", color=interaction.client.default_color, description="")
        final_embed.description += f"**Success:**\n{success}"
        final_embed.description += f"**Failed:**\n{failed}"
        await interaction.edit_original_response(embed=final_embed, content=None)




async def setup(bot):
    await bot.add_cog(Events(bot))
    await bot.add_cog(Dank_Events(bot), guilds=[discord.Object(999551299286732871), discord.Object(785839283847954433), discord.Object(947525009247707157)])