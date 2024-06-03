import discord
from discord.ext import commands

class Forums(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="close")
    @commands.has_permissions(ban_members=True)
    async def _close(self, ctx: commands.Context):

        if not isinstance(ctx.channel, discord.Thread): return await ctx.send("This command can only be used in threads.")
        if not isinstance(ctx.channel.parent, discord.ForumChannel): return await ctx.send("This command can only be used in forums.")
        if ctx.channel.parent_id != 1246360445292515390: return
        tag = ctx.channel.parent.get_tag(1247099210873180262)
        if tag is None: return await ctx.send("This forum does not have a tag.")
        await ctx.channel.add_tags(tag, reason=f"Resolved by {ctx.author.name}")
        await ctx.message.add_reaction("<a:nat_check:1010969401379536958>")
        await ctx.channel.edit(archived=True, locked=True)

async def setup(bot):
    await bot.add_cog(Forums(bot))
