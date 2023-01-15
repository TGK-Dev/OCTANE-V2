import discord
import datetime
import asyncio
from discord import app_commands
from discord.ext import commands
from utils.db import Document
from utils.views.payout_config import Config_view
from utils.transformer import MultipleMember
from utils.views.buttons import Payout_Buttton
from io import BytesIO

class Payout(commands.GroupCog, name="payout", description="Payout commands"):
    def __init__(self, bot):
        self.bot = bot
        self.bot.payout_config = Document(self.bot.db, "payout_config")
        self.bot.payout_queue = Document(self.bot.db, "payout_queue")
    
    config = app_commands.Group(name="config", description="configur the payout system settings")

    @config.command(name="show", description="configur the payout system settings")
    async def config_show(self, interaction: discord.Interaction):
        embed = discord.Embed(title="Payout Config")
        data = await self.bot.payout_config.find(interaction.guild.id)
        if data is None:
            data = {
                '_id': interaction.guild.id,
                'queue_channel': None,
                'manager_roles': [],
                'log_channel': None,
            }
            await self.bot.payout_config.insert(data)
        
        #create an 2x2 feilds in embed using embed.add_field
        embed.add_field(name="Queue Channel", value=f"{interaction.guild.get_channel(data['queue_channel']).mention if data['queue_channel'] else 'Not set'}")
        embed.add_field(name="Log Channel", value=f"{interaction.guild.get_channel(data['log_channel']).mention if data['log_channel'] else 'Not set'}", inline=True)
        embed.add_field(name="Manager Roles", value=f"{', '.join([interaction.guild.get_role(role).mention for role in data['manager_roles']]) if data['manager_roles'] else 'Not set'}",)
        
        await interaction.response.send_message(embed=embed)
    
    @config.command(name="edit", description="configur the payout system settings")
    async def config_edit(self, interaction: discord.Interaction):
        data = await self.bot.payout_config.find(interaction.guild.id)
        if data is None:
            data = {
                '_id': interaction.guild.id,
                'queue_channel': None,
                'manager_roles': [],
                'log_channel': None,
            }
            await self.bot.payout_config.insert(data)
        
        embed = discord.Embed(title="Payout Config")
        embed.add_field(name="Queue Channel", value=f"{interaction.guild.get_channel(data['queue_channel']).mention if data['queue_channel'] else 'Not set'}")
        embed.add_field(name="Log Channel", value=f"{interaction.guild.get_channel(data['log_channel']).mention if data['log_channel'] else 'Not set'}", inline=True)
        embed.add_field(name="Manager Roles", value=f"{', '.join([interaction.guild.get_role(role).mention for role in data['manager_roles']]) if data['manager_roles'] else 'Not set'}",)

        view = Config_view(data)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()
    
    @app_commands.command(name="set", description="configur the payout system settings")
    @app_commands.describe(event="event name", message_id="winner message id", winners="winner of the event", prize="what did they win?")
    async def payout_set(self, interaction: discord.Interaction, event: str, message_id: str, winners: app_commands.Transform[discord.Member, MultipleMember], prize: str):
        data = await self.bot.payout_config.find(interaction.guild.id)

        user_roles = [role.id for role in interaction.user.roles]
        if (set(user_roles) & set(data['manager_roles'])):
            pass
        else:
            return await interaction.response.send_message("You are not allowed to use this command!", ephemeral=True)

        loading_embed = discord.Embed(description=f"<a:loading:998834454292344842> | Setting up the payout for total of `{len(winners)}` winners!")
        finished_embed = discord.Embed(description=f"")        
        await interaction.response.send_message(embed=loading_embed, ephemeral=True)
        loading_emoji = await self.bot.emoji_server.fetch_emoji(998834454292344842)

        try:
            winner_message = await interaction.channel.fetch_message(message_id)
            await winner_message.add_reaction(loading_emoji)
        except discord.NotFound:
            await interaction.followup.send("I could not find that message! Please make sure the message is in this channel!", ephemeral=True)
            return
        
        data = await self.bot.payout_config.find(interaction.guild.id)
        if data is None:
            data = {
                '_id': interaction.guild.id,
                'queue_channel': None,
                'manager_roles': [],
                'log_channel': None,
            }
            await self.bot.payout_config.insert(data)
            return await interaction.followup.send("Please set up the payout config first!", ephemeral=True)
        
        if data['queue_channel'] is None:
            return await interaction.followup.send("Please set up the payout config first!", ephemeral=True)
        
        queue_channel = interaction.guild.get_channel(data['queue_channel'])
        if queue_channel is None:
            return await interaction.followup.send("Please set up the payout config first!", ephemeral=True)
        
        for winner in winners:
            if isinstance(winner, discord.Member):
                embed = discord.Embed(title="Payout Queued", color=discord.Color.random(), timestamp=datetime.datetime.now())
                embed.add_field(name="Event", value=f"**<:nat_reply_cont:1011501118163013634> {event}**")
                embed.add_field(name="Winner", value=f"**<:nat_reply_cont:1011501118163013634> {winner.mention} ({winner.name}#{winner.discriminator})**")
                embed.add_field(name="prize", value=f"**<:nat_reply_cont:1011501118163013634> {prize}**")
                embed.add_field(name="Channel", value=f"**<:nat_reply_cont:1011501118163013634> {winner_message.channel.mention}**")
                embed.add_field(name="Message Link", value=f"**<:nat_reply_cont:1011501118163013634> [Click Here]({winner_message.jump_url})**")
                embed.add_field(name="Set By", value=f"**<:nat_reply_cont:1011501118163013634> {interaction.user.mention}**")
                embed.add_field(name="Payout Status", value="**<:nat_reply_cont:1011501118163013634> Pending**")
                embed.set_footer(text=f"Message ID: {winner_message.id}", icon_url=interaction.guild.icon.url)

                msg = await queue_channel.send(embed=embed, content=f"{winner.mention}, you will be paid out in the next `24hrs`! \n> If not paid within the deadline claim from <#785901543349551104>.", view=Payout_Buttton())
                data = {
					'_id': msg.id,
					'channel': winner_message.channel.id,
					'guild': interaction.guild.id,
					'event': event,
					'winner': winner.id,
					'prize': prize,
					'set_by': interaction.user.id,
					'winner_message_id': winner_message.id,
				}
                try:
                    await self.bot.payout_queue.insert(data)
                    loading_embed.description += f"\n <:octane_yes:1019957051721535618> | Payout Successfully queued for {winner.mention} ({winner.name}#{winner.discriminator})"
                    finished_embed.description += f"\n <:octane_yes:1019957051721535618> | Payout Successfully queued for {winner.mention} ({winner.name}#{winner.discriminator})"

                except Exception as e:

                    loading_embed.description += f"\n <:dynoError:1000351802702692442> | Failed to queue payout for {winner.mention} ({winner.name}#{winner.discriminator})"
                    finished_embed.description += f"\n <:dynoError:1000351802702692442> | Failed to queue payout for {winner.mention} ({winner.name}#{winner.discriminator})"
                
                await interaction.edit_original_response(embed=loading_embed)
                await asyncio.sleep(1)
            
        link_view = discord.ui.View()
        link_view.add_item(discord.ui.Button(label="Go to Payout-Queue", url=msg.jump_url))
        finished_embed.description += f"\n**<:nat_reply_cont:1011501118163013634> Successfully queued {len(winners)}**"
        await interaction.edit_original_response(embed=finished_embed, view=link_view)
    
    @app_commands.command(name="delete", description="Delete a payout from the queue")
    @app_commands.describe(message_id="The message id of the payout you want to delete")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def payout_delete(self, interaction: discord.Interaction, message_id: str):
        message_id = int(message_id)
        data = await self.bot.payout_queue.find(message_id)
        config = await self.bot.payout_config.find(interaction.guild.id)
        if data is None:
            return await interaction.response.send_message("That payout is not in the queue!", ephemeral=True)
        if config is None:
            return await interaction.response.send_message("Please set up the payout config first!", ephemeral=True)
        if config['queue_channel'] is None:
            return await interaction.response.send_message("Please set up the payout config first!", ephemeral=True)

        queue_channel = interaction.guild.get_channel(config['queue_channel'])
        winner_channel = interaction.guild.get_channel(data['channel'])
        loading_emoji = await self.bot.emoji_server.fetch_emoji(998834454292344842)


        try:
            winner_message = await winner_channel.fetch_message(data['winner_message_id'])
            queue_message = await queue_channel.fetch_message(message_id)
            await queue_message.delete()
            await winner_message.remove_reaction(loading_emoji, self.bot.user)
        except Exception as e:
            await interaction.response.send_message(embed = discord.Embed(title="Error", description=f"Failed to fetch the message from the winner channel or the queue channel. \n> {e}", color=discord.Color.red()), ephemeral=True)
            
        await self.bot.payout_queue.delete(message_id)
        await interaction.response.send_message("Successfully deleted the payout!", ephemeral=True)

class Dump(commands.GroupCog, name="dump", description="Dump commands"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="role", description="Dump a role")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.describe(role="The role to dump")
    async def dump_role(self, interaction: discord.Interaction, role: discord.Role):
        if len(role.members) <= 30:
            msg = ""
            for member in role.members:
                msg += f"{member.name}#{member.discriminator} ({member.id})\n"
            await interaction.response.send_message(msg, ephemeral=False)
        else:
            await interaction.response.send_message("Too many members in the role! creating a file...", ephemeral=False)
            msg = ""
            for member in role.members:
                msg += f"{member.name}#{member.discriminator} ({member.id})\n"
            buffer = BytesIO(msg.encode('utf-8'))
            file = discord.File(buffer, filename=f"{role.name}.txt")
            buffer.close()
            await interaction.edit_original_response(content="Here you go!", attachments=[file])

    @app_commands.command(name="invite", description="dump an invite")
    @app_commands.describe(user="The user to dump the invites from")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def dump_invite(self, interaction: discord.Interaction, user: discord.Member):
        data = await self.bot.invites.find(user.id)
        if data is None:
            return await interaction.response.send_message("User has no invites!", ephemeral=True)

        if len(data['invites']) <= 30:
            msg = ""
            for invite in data['invites']:
                msg += f"{invite}\n"
            await interaction.response.send_message(msg, ephemeral=False)
        else:
            await interaction.response.send_message("Too many invites! creating a file...", ephemeral=False)
            msg = ""
            for invite in data['invites']:
                msg += f"{invite}\n"
            buffer = BytesIO(msg.encode('utf-8'))
            file = discord.File(buffer, filename=f"{user.name}.txt")
            buffer.close()
            await interaction.edit_original_response(content="Here you go!", attachments=[file])

async def setup(bot):
    await bot.add_cog(Payout(bot))
    await bot.add_cog(Dump(bot))