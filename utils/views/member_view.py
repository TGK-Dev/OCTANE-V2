import discord
from discord import Interaction, SelectOption
from discord.ui import View, Button, button, TextInput, Item
from .selects import Role_select, Select_General, Channel_select
from .modal import General_Modal


class Member_view(discord.ui.View):
    def __init__(self, bot,member: discord.Member, interaction: discord.Interaction):
        self.member = member
        self.author = interaction.user
        self.message = None
        self.bot = bot
        super().__init__(timeout=120)
    
    async def interaction_check(self, interaction: Interaction):
        if interaction.user.id == self.author.id:
            return True
        else:
            await interaction.response.send_message("You are not the owner of this command", ephemeral=True)
            return False
    
    async def on_timeout(self):
        for child in self.children:child.disabled = True; await self.message.edit(view=self)

    @discord.ui.select(placeholder="Select Page", custom_id="MEMBER_VIEW", max_values=1,
                        options=[
                        discord.SelectOption(label="Profile", value="profile"),
                        discord.SelectOption(label="Badge", value="badge", emoji="<:bage:991740849664819332>"),
                        discord.SelectOption(label="Roles", value="roles", emoji="<:tgk_role:1073908306713780284>"),
                        discord.SelectOption(label="Votes", value="votes")])
    async def member_view(self, interaction: discord.Interaction, select: discord.ui.Select):
        choice = select.values[0]

        match choice:
            case "profile":
                embed = discord.Embed(title=f"User Info - {self.member.name}#{self.member.discriminator}")
                embed.set_thumbnail(url=self.member.avatar.url if self.member.avatar else self.member.default_avatar.url)

                embed.add_field(name="<:authorized:991735095587254364> ID:", value=self.member.id)
                embed.add_field(name="<:displayname:991733326857654312> Display Name:", value=self.member.display_name)

                embed.add_field(name="<:bot:991733628935610388> Bot Account:", value=self.member.bot)                

                embed.add_field(name="<:settings:991733871118917683> Account creation:", value=self.member.created_at.strftime('%d/%m/%Y %H:%M:%S'))
                embed.add_field(name="<:join:991733999477203054> Server join:", value=self.member.joined_at.strftime('%d/%m/%Y %H:%M:%S'))
                await interaction.response.edit_message(embed=embed)
        
            case "badge":

                embed = discord.Embed(title=f"Badges - {self.member.name}#{self.member.discriminator}")
                badge = ""            
                if self.member.id in interaction.client.owner_ids:
                    badge += "Owner | <:tgk_owner:1073588580796092558>\n"
                    badge += "Developer | <:tgk_dev:1076842962509639801>\n"
                
                if self.member.guild_permissions.administrator:
                    badge += "Administrator | <a:admin:992043062874361866>\n"
                
                if self.member.guild_permissions.manage_messages:
                    badge += "Moderator | <:mod:992043856197595187>\n"
                
                if discord.utils.get(self.member.guild.roles, id=818129661325869058) in self.member.roles:
                    badge += "Staff Team | <:staff:992044132644175934>\n"
                
                if self.member.premium_since is not None:
                    badge += "Booster | <a:booster:992039182442704966>\n"
                
                if discord.utils.get(self.member.guild.roles, id=931072410365607946) in self.member.roles:
                    badge += "First 50 Members  | <a:real_og:992048421974315051>\n"
                
                if discord.utils.get(self.member.guild.roles, id=786884615192313866) in self.member.roles:
                    badge += "Voted | <:TGK_vote:942521024476487741>"
                
                if badge == "":
                    badge = "None"
                
                embed = discord.Embed(title=f"Badges - {self.member.name}#{self.member.discriminator}", description=badge, color=interaction.client.default_color)
                await interaction.response.edit_message(embed=embed)
            
            case "roles":
                embed = discord.Embed(title=f"Roles - {self.member.name}#{self.member.discriminator}", color=interaction.client.default_color)
                roles = ""
                list_role = sorted(self.member.roles, reverse=True)
                for role in list_role:
                    if len(roles) <= 2000:
                        roles += f"{role.mention} | `{role.id}`\n"
                    else:
                        embed.set_footer(text="And More ....")
                        break
                embed.description = roles
                await interaction.response.edit_message(embed=embed)
            
            case "votes":
                embed = discord.Embed(title=f"Votes - {self.member.name}#{self.member.discriminator}", color=interaction.client.default_color)
                votes_data = await self.bot.votes.find(self.member.id)
                if votes_data is None:
                    embed.description = f"No Votes"
                elif votes_data is not None:
                    embed.description = f"**Total Votes:** {votes_data['votes']}\n"
                    embed.description += f"**Vote Streak:** {votes_data['streak']}\n"
                    embed.description += f"**Last Vote:** <t:{round(votes_data['last_vote'].timestamp())}:R>"

                await interaction.response.edit_message(embed=embed)
