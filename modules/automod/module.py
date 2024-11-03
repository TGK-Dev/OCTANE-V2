import random
import discord
import datetime
from discord.ext import commands
from discord import app_commands, Interaction
from utils.db import Document
from typing import TypedDict, List


class AutoModGuildConfig(TypedDict):
    _id: int
    guild_id: int
    working_trigger_ids: list[int]


message_actions_dict = {
    1: {
        "message": "⚠️ Attention {user}: Your message triggered the automod. Please review the rules to avoid future issues."
    },
    2: {
        "message": "⚔️ My, my... {user}, you dare disturb the peace of my realm? Consider this your first and final warning, insignificant one. 👑"
    },
    3: {
        "message": "😾 How... disappointing, {user}. I was in the midst of petting Mr. Whiskers, my demonic familiar. One minute in the void for interrupting our bonding time. <a:cat_pat:1302615929724862554>",
        "duration": 1,
    },
    4: {
        "message": "💀 Fool. {user} thought they could challenge my authority? Five minutes in the shadow realm should crush your pathetic rebellion. 🔥",
        "duration": 5,
    },
    5: {
        "message": "⚡ Fifteen minutes of banishment! Witness my power, {user}, as I cast you into the abyss. Your defiance amuses me, worm. 👁️",
        "duration": 15,
    },
    6: {
        "message": "😾 *sigh* {user},I was just about to serve dinner to my legion of feline overlords when you dared to summon me. 30 minutes of exile. No one interrupts Lord Mittens' <:peepowithcatto:1271485194620243988> dinner time. ⛓️",
        "duration": 30,
    },
    7: {
        "message": "🗝️ Behold, my mercy has reached its end, {user}. One hour in the depths of silence. Let this be a testament to my absolute dominion. 👑",
        "duration": 60,
    },
    8: {
        "message": "🌑 Two hours of exile for the defiant {user}. Your persistence in rebellion only proves your inferiority. Bow before my might. ⚔️",
        "duration": 120,
    },
    9: {
        "message": "💫 Six hours in the dark dimension. {user}, your continued existence tests my godlike patience. Suffer in isolation. 🏰",
        "duration": 360,
    },
    10: {
        "message": "⚜️ At last, {user}, you have achieved your destiny: 24 hours in the void. I am your god now, and this is my divine punishment. *slight chuckle* ⚡",
        "duration": 1440,
    },
}

message_actions_dict_parent_theme = {
    1: {
        "message": "⚠️ Attention {user}: Your message triggered the automod. Please review the rules to avoid future issues."
    },
    2: {
        "message": "🤦 {user}, sweetie... we've talked about this. What did we say about behaving in the server? 🫂"
    },
    3: {
        "message": "😔 {user}, I'm not mad, I'm just disappointed. Go sit in timeout for a minute and think about what you've done. 💝",
        "duration": 1,
    },
    4: {
        "message": "🫡 Well well well, if it isn't {user}... back at it again. Five minutes in your room, young person. We raised you better than this. 🏠",
        "duration": 5,
    },
    5: {
        "message": "🎭 {user}, honey... I got a message from the other mods about your behavior. 15 minutes, no discord, go do your homework. 📚",
        "duration": 15,
    },
    6: {
        "message": "😮‍💨 {user}... *deep parental sigh* That's it - 30 minutes timeout. Wait till your other moderator hears about this. 📱",
        "duration": 30,
    },
    7: {
        "message": "📝 {user}, I'm writing an email to your Discord account about your behavior. One hour, no chatting, and please reflect on your choices. 💌",
        "duration": 60,
    },
    8: {
        "message": "🤷 That's it {user}, I'm taking away your chatting privileges for two hours. Don't make me come back there! 😤",
        "duration": 120,
    },
    9: {
        "message": "😑 {user}, you're grounded for six hours. And yes, we will be having a long talk about this when you get back. 🪑",
        "duration": 360,
    },
    10: {
        "message": "📵 {user}, you are OFFICIALLY grounded for 24 hours! No Discord, no gaming, go touch grass. We'll discuss your behavior tomorrow, young person! 🌱",
        "duration": 1440,
    },
}

message_actions_dict_cring = {
    1: {
        "message": "😳 Um, so like, {user}, I just wanted to confess that your message triggered automod. No big deal, right? 🙈"
    },
    2: {
        "message": "🙋‍♂️ Hey, it’s me again! {user}, you’re really pushing it now. Next up: a one-way ticket to timeout-ville. 🏝️"
    },
    3: {
        "message": "🤦‍♂️ Okay, {user}, I might have to admit I was hoping you’d listen. Enjoy this mini timeout while you think about your choices. 😅",
        "duration": 1,
    },
    4: {
        "message": "📉 Ugh, {user}, it’s like you want attention! Here’s a longer timeout for your dramatic flair. Hope you’re enjoying the limelight! 🎭",
        "duration": 5,
    },
    5: {
        "message": "😱 {user}, you’ve officially turned this into a reality show! Welcome to your extended timeout. Let’s hope for a plot twist! 📚",
        "duration": 15,
    },
    6: {
        "message": "🎬 Oh dear, {user}, you’re practically starring in the Timeout Chronicles! Here’s an even longer stay to reflect on your choices. 📺",
        "duration": 30,
    },
    7: {
        "message": "📺 Seriously, {user}? At this point, you’re a permanent character in the Timeout saga! Here’s another hour for your ‘fan-favorite’ status. 😂",
        "duration": 60,
    },
    8: {
        "message": "💔 {user}, we’re making this a series! Time for another extended timeout. Maybe take a breather and come back with a better storyline. 💤",
        "duration": 120,
    },
    9: {
        "message": "🚫 Oh my gosh, {user}, you’re back for more drama? Here’s a 6-hour timeout. Let’s see if you can come back with less chaos! 🤞",
        "duration": 360,
    },
    10: {
        "message": "🛑 *GASP!* {user}, you’ve unlocked the ultimate timeout: 24 hours of reflection. Make it count, darling! We’ll see you on the next episode! 🌟",
        "duration": 1440,
    },
}


@app_commands.guild_only()
@app_commands.default_permissions(ban_members=True)
class AutoMod(commands.GroupCog, description="Automod commands"):
    def __init__(self, bot):
        self.bot = bot
        self.automod_confifg = Document(self.bot.db, "automod_config")
        self.offenders = {}

    async def rule_auto(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        rules = []
        guild_rules = await interaction.guild.fetch_automod_rules()
        for rule in guild_rules:
            rules.append(app_commands.Choice(name=rule.name, value=str(rule.id)))
        if rules == []:
            rules.append(app_commands.Choice(name="No rules found", value="None"))
        return rules[:24]

    perm = discord.Permissions()
    perm.ban_members = True

    @app_commands.command(
        name="auto-punish", description="Enable/Disable custom automod punishment"
    )
    @app_commands.autocomplete(rule=rule_auto)
    async def auto_punish(self, interaction: Interaction, rule: str):
        rule: discord.AutoModRule = await interaction.guild.fetch_automod_rule(
            int(rule)
        )
        guild_config = await self.automod_confifg.find(interaction.guild.id)
        if not guild_config:
            guild_config = {
                "_id": interaction.guild.id,
                "guild_id": interaction.guild.id,
                "working_trigger_ids": [rule.id],
            }
            await self.automod_confifg.insert(guild_config)
        else:
            if rule.id in guild_config["working_trigger_ids"]:
                guild_config["working_trigger_ids"].remove(rule.id)
            else:
                guild_config["working_trigger_ids"].append(rule.id)
            await self.automod_confifg.update(guild_config)
        await interaction.response.send_message(
            f"Auto punish for {rule.name} is {'enabled' if rule.id in guild_config['working_trigger_ids'] else 'disabled'}",
            ephemeral=True,
        )

    @app_commands.command(
        name="offece-reset",
        description="Reset the offenses for a user",
    )
    async def offense_reset(self, interaction: Interaction):
        user = interaction.target
        if user.id in self.offenders.keys():
            if interaction.guild.id in self.offenders[user.id].keys():
                del self.offenders[user.id][interaction.guild.id]

            await interaction.response.send_message(
                f"Offenses for {user.mention} has been reset",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"No offenses found for {user.mention}",
                ephemeral=True,
            )

    @app_commands.command(
        name="offense",
        description="View the offenses for a user",
    )
    async def offense(self, interaction: Interaction):
        user = interaction.target
        if user.id in self.offenders.keys():
            if interaction.guild.id in self.offenders[user.id].keys():
                await interaction.response.send_message(
                    f"Offenses for {user.mention} in {interaction.guild.name}: {len(self.offenders[user.id][interaction.guild.id])}",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    f"No offenses found for {user.mention}",
                    ephemeral=True,
                )
        else:
            await interaction.response.send_message(
                f"No offenses found for {user.mention}",
                ephemeral=True,
            )

    @app_commands.command(
        name="view-rules",
        description="View auto punish rules",
    )
    async def view_rules(self, interaction: Interaction):
        embed = discord.Embed(title="Auto Punish Rules", description="")
        rules = await interaction.guild.fetch_automod_rules()
        guild_config = await self.automod_confifg.find(interaction.guild.id)
        if not guild_config:
            guild_config = {
                "_id": interaction.guild.id,
                "guild_id": interaction.guild.id,
                "working_trigger_ids": [],
            }
            await self.automod_confifg.insert(guild_config)
        for rule in rules:
            if rule.id in guild_config["working_trigger_ids"]:
                embed.description += f"{rule.name} - Enabled\n"
            else:
                embed.description += f"{rule.name} - Disabled\n"

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_automod_action(self, execution: discord.AutoModAction):
        if execution.guild.id not in [785839283847954433, 999551299286732871]:
            return
        guild_config: AutoModGuildConfig = await self.automod_confifg.find(
            execution.guild.id
        )
        guild = execution.guild
        if not guild_config:
            return
        if execution.rule_id not in guild_config["working_trigger_ids"]:
            return
        if execution.member.id in self.offenders.keys():
            if guild.id in self.offenders[execution.member.id].keys():
                self.offenders[execution.member.id][guild.id].append(
                    {
                        "offense_at": discord.utils.utcnow(),
                    }
                )
            else:
                self.offenders[execution.member.id][guild.id] = [
                    {
                        "offense_at": discord.utils.utcnow(),
                    }
                ]
        else:
            self.offenders[execution.member.id] = {
                guild.id: [
                    {
                        "offense_at": discord.utils.utcnow(),
                    }
                ]
            }
        try:
            message_pack = random.choice(
                [
                    message_actions_dict,
                    message_actions_dict_parent_theme,
                    message_actions_dict_cring,
                ]
            )
            action = message_pack[len(self.offenders[execution.member.id][guild.id])]
        except KeyError:
            action = message_actions_dict[10]

        message = action["message"].format(user=execution.member.mention)
        if "duration" in action.keys():
            user = execution.member
            await user.timeout(
                discord.utils.utcnow()
                + datetime.timedelta(seconds=60 * action["duration"]),
                reason="Automod Punishment",
            )
        await execution.channel.send(
            message, delete_after=10 * 3 if "duration" in action.keys() else 10
        )


async def setup(bot):
    await bot.add_cog(
        AutoMod(bot),
        guilds=[discord.Object(999551299286732871), discord.Object(785839283847954433)],
    )
