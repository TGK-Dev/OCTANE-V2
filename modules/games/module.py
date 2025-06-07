import discord
from discord.ext import commands
from discord import app_commands
from .views import Minesweeper
from .tictactoe import TicTacToe
from typing import Literal
import asyncio


class Games(commands.GroupCog, name="games", description="Games commands"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="minesweeper", description="Play Minesweeper")
    async def minesweeper(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎮 Minesweeper",
            description="Click the buttons to reveal cells. Avoid the mines!",
            color=discord.Color.blue(),
        )
        embed.set_footer(text=f"Game started by {interaction.user.display_name}")

        await interaction.response.send_message(
            embed=embed,
            view=Minesweeper(interaction.user),
            ephemeral=False,
        )

    @app_commands.command(name="tictactoe", description="Play Tic Tac Toe")
    @app_commands.describe(
        opponent="The user you want to play against",
        ai="Play against AI with selected difficulty",
    )
    async def tictactoe(
        self,
        interaction: discord.Interaction,
        ai: Literal["Rookie", "Veteran", "Pro"] = None,
        opponent: discord.Member = None,
    ):
        # Handle validation
        if ai is None and opponent is None:
            await interaction.response.send_message(
                "You must either select an AI difficulty or mention a player to play against.",
                ephemeral=True,
            )
            return

        if ai is not None and opponent is not None:
            await interaction.response.send_message(
                "You can't play against both AI and a player at the same time.",
                ephemeral=True,
            )
            return

        if opponent == interaction.user:
            await interaction.response.send_message(
                "You can't play against yourself!",
                ephemeral=True,
            )
            return

        # Initialize the game
        if ai is not None:
            # Player vs AI
            view = TicTacToe(interaction.user, ai_difficulty=ai)

            # Determine which symbol each player is using based on who goes first
            player_symbol = "❌" if view.first_player_is_x else "⭕"
            ai_symbol = "⭕" if view.first_player_is_x else "❌"

            # Create appropriate embed
            embed = discord.Embed(
                title=f"🎮 Tic Tac Toe: Player vs AI ({ai})",
                description=f"{interaction.user.mention} vs AI ({ai})",
                color=discord.Color.gold(),
            )
            embed.add_field(
                name="Player",
                value=f"{interaction.user.mention} {player_symbol}",
                inline=True,
            )
            embed.add_field(name="AI", value=f"AI ({ai}) {ai_symbol}", inline=True)

            if view.current_player == interaction.user:
                embed.add_field(
                    name="Turn",
                    value=f"It's your turn, {interaction.user.mention}!",
                    inline=False,
                )
            else:
                embed.add_field(
                    name="Turn",
                    value="AI is making the first move...",
                    inline=False,
                )
                # Schedule AI to make the first move after the view is sent
                self.bot.loop.create_task(self.ai_first_move(view, interaction))

            await interaction.response.send_message(
                embed=embed,
                view=view,
                ephemeral=False,
            )
        else:
            # Player vs Player
            view = TicTacToe(interaction.user, opponent)

            first_player = interaction.user if view.first_player_is_x else opponent
            p1_symbol = "❌" if view.first_player_is_x else "⭕"
            p2_symbol = "⭕" if view.first_player_is_x else "❌"

            embed = discord.Embed(
                title="🎮 Tic Tac Toe: Player vs Player",
                description=f"{interaction.user.mention} vs {opponent.mention}",
                color=discord.Color.green(),
            )
            embed.add_field(
                name="Player 1",
                value=f"{interaction.user.mention} {p1_symbol}",
                inline=True,
            )
            embed.add_field(
                name="Player 2",
                value=f"{opponent.mention} {p2_symbol}",
                inline=True,
            )
            embed.add_field(
                name="Turn",
                value=f"It's {first_player.mention}'s turn!",
                inline=False,
            )

            await interaction.response.send_message(
                embed=embed,
                view=view,
                ephemeral=False,
            )

    async def ai_first_move(self, view, interaction):
        """Handle AI making the first move"""
        # Wait a short time for the message to be properly displayed
        await asyncio.sleep(0.5)

        # Get the message to update after AI moves
        message = await interaction.original_response()

        # Let AI make its move
        await view.ai_turn()

        # Update the embed for the player's turn
        embed = discord.Embed(
            title=f"🎮 Tic Tac Toe: Player vs AI ({view.ai_difficulty})",
            description=f"{interaction.user.mention} vs AI ({view.ai_difficulty})",
            color=discord.Color.gold(),
        )

        player_symbol = "❌" if view.first_player_is_x else "⭕"
        ai_symbol = "⭕" if view.first_player_is_x else "❌"

        embed.add_field(
            name="Player",
            value=f"{interaction.user.mention} {player_symbol}",
            inline=True,
        )
        embed.add_field(
            name="AI", value=f"AI ({view.ai_difficulty}) {ai_symbol}", inline=True
        )
        embed.add_field(
            name="Turn",
            value=f"Your turn, {interaction.user.mention}!",
            inline=False,
        )

        await message.edit(embed=embed, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(Games(bot))
