import discord
from discord.ext import commands


class Swan(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def is_me():
        def predicate(ctx: commands.Context):
            return ctx.guild.id == 1379071789182881884

        return commands.check(predicate)

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{self.__class__.__name__} is ready!")

    @commands.command(
        name="verify",
        description="Verify yourself to access the server.",
        aliases=["v"],
    )
    @is_me()
    @commands.has_permissions(manage_roles=True)
    async def verify(self, ctx: commands.Context, member: discord.Member):
        """Verify a member to give them access to the server."""

        role = ctx.guild.get_role(1380538780234154034)
        veriy_role = ctx.guild.get_role(1379689865960226926)
        if not role:
            embed = discord.Embed(
                title="Error",
                description="Verification role not found.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            return
        if role not in member.roles:
            embed = discord.Embed(
                title="Already Verified",
                description="User already verified.",
                color=discord.Color.orange(),
            )
            await ctx.send(embed=embed)
            return
        try:
            await member.remove_roles(role)
            await member.add_roles(veriy_role)
            embed = discord.Embed(
                title="Access Granted",
                description=f"{member.mention} has allowed access to the server.",
                color=discord.Color.green(),
            )
            await ctx.send(embed=embed, delete_after=2)
            # Send welcome message to channel 1379071789182881887
            welcome_channel = ctx.guild.get_channel(1379071789182881887)
            if welcome_channel:
                await welcome_channel.send(f"Welcome {member.mention} to the server!")
            await ctx.message.delete()
        except discord.Forbidden:
            embed = discord.Embed(
                title="Permission Error",
                description="I do not have permission to manage roles.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Swan(bot))
    print(f"{Swan.__name__} has been loaded.")
