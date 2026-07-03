import discord
from discord.ext import commands


class HoneyPot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        if message.channel.id in [1522572261683630181, 1522573430338228346]:
            if not (
                message.author.guild_permissions.administrator
                or message.author.guild_permissions.manage_messages
            ):
                await message.delete()
                try:
                    await message.author.send(
                        "You fall for the honeypot! you are banned from the server if you recover this message request a unban from appeal server https://discord.gg/e994RysRqZ"
                    )
                except discord.HttpException:
                    pass
                await message.guild.ban(message.author, reason="Fell for the honeypot")
                logc = self.bot.get_channel(1190668526361518120)
                await logc.send(
                    f"{message.author} fell for the honeypot and was banned from the server."
                )


async def setup(bot):
    await bot.add_cog(HoneyPot(bot))
