import discord
from discord.ui import View, Button
import random


class TicTacToeButton(Button):
    def __init__(self, x, y):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="\u200b",
            row=y,
        )
        self.x = x
        self.y = y
        self.value = None


class TicTacToe(View):
    X = "❌"
    O = "⭕"
    Tie = "🔄"

    def __init__(
        self,
        player1: discord.Member,
        player2: discord.Member = None,
        ai_difficulty: str = None,
    ):
        super().__init__(timeout=180)
        self.player1 = player1  # X
        self.player2 = player2  # O
        self.ai_difficulty = ai_difficulty
        self.is_ai_game = ai_difficulty is not None

        # Randomly decide who goes first
        self.first_player_is_x = random.choice([True, False])
        self.current_player = self.player1 if self.first_player_is_x else self.player2

        self.board = [[None for _ in range(3)] for _ in range(3)]
        self.winner = None
        self.turn_message = None

        # If AI game, set a placeholder for player2
        if self.is_ai_game:
            self.ai_name = f"AI ({ai_difficulty})"

        # Initialize the board
        for y in range(3):
            for x in range(3):
                button = TicTacToeButton(x, y)
                button.callback = self.make_callback(x, y)
                self.board[y][x] = button
                self.add_item(button)

    async def interaction_check(self, interaction):
        # Check if it's the player's turn
        if self.is_ai_game:
            # In AI mode, only player1 can interact
            if interaction.user != self.player1:
                await interaction.response.send_message(
                    "This is not your game!", ephemeral=True
                )
                return False
        else:
            # In PvP mode, check if it's the player's turn
            if interaction.user not in (self.player1, self.player2):
                await interaction.response.send_message(
                    "This is not your game!", ephemeral=True
                )
                return False

            if interaction.user != self.current_player:
                await interaction.response.send_message(
                    "It's not your turn!", ephemeral=True
                )
                return False

        return True

    def make_callback(self, x, y):
        async def button_callback(interaction):
            await self._handle_click(interaction, x, y)

        return button_callback

    async def _handle_click(self, interaction, x, y):
        button = self.board[y][x]

        # Check if button is already marked
        if button.value is not None:
            await interaction.response.send_message(
                "That position is already marked!", ephemeral=True
            )
            return

        # Mark the button with the current player's symbol
        symbol = self.X if self.current_player == self.player1 else self.O
        button.value = symbol
        button.label = symbol
        button.disabled = True
        button.style = discord.ButtonStyle.gray

        # Check if game is over
        game_over = self.check_winner()

        if game_over:
            await self.end_game(interaction)
        else:
            # Switch players
            self.current_player = (
                self.player2 if self.current_player == self.player1 else self.player1
            )

            # Handle AI turn if enabled
            if self.is_ai_game and self.current_player == self.player2:
                # First update the message for AI turn
                embed = discord.Embed(
                    title=f"🎮 Tic Tac Toe: Player vs AI ({self.ai_difficulty})",
                    description=f"{self.player1.mention} vs {self.ai_name}",
                    color=discord.Color.gold(),
                )

                player_symbol = "❌" if self.first_player_is_x else "⭕"
                ai_symbol = "⭕" if self.first_player_is_x else "❌"

                embed.add_field(
                    name="Player",
                    value=f"{self.player1.mention} {player_symbol}",
                    inline=True,
                )
                embed.add_field(
                    name="AI", value=f"{self.ai_name} {ai_symbol}", inline=True
                )
                embed.add_field(name="Status", value="AI is thinking...", inline=False)

                await interaction.response.edit_message(
                    embed=embed,
                    view=self,
                )

                # Get the message object for later editing
                original_message = await interaction.original_response()

                # Make AI move immediately (no delay)
                await self.ai_turn()

                # Check if AI won
                if self.check_winner():
                    if self.winner == self.Tie:
                        result_embed = discord.Embed(
                            title="🎮 Tic Tac Toe: Game Over",
                            description="It's a tie!",
                            color=discord.Color.greyple(),
                        )
                    else:
                        result_embed = discord.Embed(
                            title="🎮 Tic Tac Toe: Game Over",
                            description=f"{self.ai_name} wins!",
                            color=discord.Color.red(),
                        )

                    # Disable all buttons
                    for y in range(3):
                        for x in range(3):
                            self.board[y][x].disabled = True

                    await original_message.edit(embed=result_embed, view=self)
                    return

                # AI didn't win, update message for player's turn
                player_turn_embed = discord.Embed(
                    title=f"🎮 Tic Tac Toe: Player vs AI ({self.ai_difficulty})",
                    description=f"{self.player1.mention} vs {self.ai_name}",
                    color=discord.Color.gold(),
                )

                player_turn_embed.add_field(
                    name="Player",
                    value=f"{self.player1.mention} {player_symbol}",
                    inline=True,
                )
                player_turn_embed.add_field(
                    name="AI", value=f"{self.ai_name} {ai_symbol}", inline=True
                )
                player_turn_embed.add_field(
                    name="Turn",
                    value=f"Your turn, {self.player1.mention}!",
                    inline=False,
                )

                await original_message.edit(embed=player_turn_embed, view=self)
            else:
                # Regular PvP turn change
                embed = discord.Embed(
                    title="🎮 Tic Tac Toe: Player vs Player",
                    description="Game in progress",
                    color=discord.Color.green(),
                )

                p1_symbol = "❌" if self.first_player_is_x else "⭕"
                p2_symbol = "⭕" if self.first_player_is_x else "❌"

                embed.add_field(
                    name="Player 1",
                    value=f"{self.player1.mention} {p1_symbol}",
                    inline=True,
                )
                embed.add_field(
                    name="Player 2",
                    value=f"{self.player2.mention} {p2_symbol}",
                    inline=True,
                )
                embed.add_field(
                    name="Turn",
                    value=f"It's {self.current_player.mention}'s turn!",
                    inline=False,
                )

                await interaction.response.edit_message(embed=embed, view=self)

    async def end_game(self, interaction, ai_turn=False):
        # Disable all buttons
        for y in range(3):
            for x in range(3):
                self.board[y][x].disabled = True

        # Create result embed
        if self.winner == self.Tie:
            result_embed = discord.Embed(
                title="🎮 Tic Tac Toe: Game Over",
                description="It's a tie!",
                color=discord.Color.greyple(),
            )
        elif self.winner == self.player1:
            result_embed = discord.Embed(
                title="🎮 Tic Tac Toe: Game Over",
                description=f"{self.player1.mention} wins!",
                color=discord.Color.blue(),
            )
        else:
            if self.is_ai_game:
                result_embed = discord.Embed(
                    title="🎮 Tic Tac Toe: Game Over",
                    description=f"{self.ai_name} wins!",
                    color=discord.Color.red(),
                )
            else:
                result_embed = discord.Embed(
                    title="🎮 Tic Tac Toe: Game Over",
                    description=f"{self.player2.mention} wins!",
                    color=discord.Color.green(),
                )

        # Update the message with the result
        await interaction.response.edit_message(embed=result_embed, view=self)

    async def ai_turn(self):
        # Find an available move based on AI difficulty
        move = None

        if self.ai_difficulty == "Pro":
            move = self.get_best_move_alpha_beta()
        elif self.ai_difficulty == "Veteran":
            move = self.get_veteran_move()
        else:  # Rookie or fallback
            move = self.get_rookie_move()

        # Make the move
        x, y = move
        button = self.board[y][x]
        button.value = self.O
        button.label = self.O
        button.disabled = True
        button.style = discord.ButtonStyle.gray

        # Switch back to player
        self.current_player = self.player1

    def get_rookie_move(self):
        # Simple random move for rookie AI
        available_moves = []
        for y in range(3):
            for x in range(3):
                if self.board[y][x].value is None:
                    available_moves.append((x, y))

        return random.choice(available_moves) if available_moves else None

    # Improved veteran AI with better strategy
    def get_veteran_move(self):
        # First check if AI can win
        winning_move = self.find_winning_move(self.O)
        if winning_move:
            return winning_move

        # Block player from winning
        blocking_move = self.find_winning_move(self.X)
        if blocking_move:
            return blocking_move

        # Take center if available - best opening strategy
        if self.board[1][1].value is None:
            return (1, 1)

        # Take corners if available - good strategic positions
        corners = [(0, 0), (0, 2), (2, 0), (2, 2)]
        random.shuffle(corners)  # Add some randomness to corner selection
        for x, y in corners:
            if self.board[y][x].value is None:
                return (x, y)

        # Take any available edge
        edges = [(0, 1), (1, 0), (1, 2), (2, 1)]
        random.shuffle(edges)
        for x, y in edges:
            if self.board[y][x].value is None:
                return (x, y)

        # Fallback to random (shouldn't get here if board has valid moves)
        return self.get_rookie_move()

    # Helper method for veteran AI to find winning moves
    def find_winning_move(self, symbol):
        # Check rows, columns, and diagonals for potential wins
        for y in range(3):
            for x in range(3):
                if self.board[y][x].value is None:
                    # Try this move
                    self.board[y][x].value = symbol
                    winner = self.evaluate()
                    self.board[y][x].value = None

                    if winner == symbol:
                        return (x, y)
        return None

    # New alpha-beta pruning implementation for Pro AI
    def get_best_move_alpha_beta(self):
        best_score = float("-inf")
        best_move = None
        alpha = float("-inf")
        beta = float("inf")

        # Check center first - often the best opening move
        if self.board[1][1].value is None:
            return (1, 1)

        # Prioritize evaluation of stronger positions (corners first)
        positions = []
        # Add corners
        for y, x in [(0, 0), (0, 2), (2, 0), (2, 2)]:
            if self.board[y][x].value is None:
                positions.append((x, y))
        # Then add edges
        for y, x in [(0, 1), (1, 0), (1, 2), (2, 1)]:
            if self.board[y][x].value is None:
                positions.append((x, y))
        # Add center if somehow not already handled
        if self.board[1][1].value is None and (1, 1) not in positions:
            positions.append((1, 1))

        # If empty board, just return center for efficiency
        if len(positions) == 9:
            return (1, 1)

        for x, y in positions:
            self.board[y][x].value = self.O
            score = self.minimax_alpha_beta(0, False, alpha, beta)
            self.board[y][x].value = None

            if score > best_score:
                best_score = score
                best_move = (x, y)

            # For equal scores, add some randomness to make AI less predictable
            elif score == best_score and random.choice([True, False]):
                best_move = (x, y)

            # Alpha-beta update
            alpha = max(alpha, best_score)

        return best_move if best_move else self.get_rookie_move()

    # Minimax with alpha-beta pruning
    def minimax_alpha_beta(self, depth, is_maximizing, alpha, beta):
        # Check for terminal states
        winner = self.evaluate()
        if winner == self.O:
            return 10 - depth  # Favor quicker wins
        elif winner == self.X:
            return -10 + depth  # Prefer delaying losses
        elif winner == self.Tie:
            return 0

        # Depth cutoff to improve performance on larger boards
        if depth >= 9:  # Maximum depth for 3x3 board
            return 0

        if is_maximizing:
            best_score = float("-inf")
            for y in range(3):
                for x in range(3):
                    if self.board[y][x].value is None:
                        self.board[y][x].value = self.O
                        score = self.minimax_alpha_beta(depth + 1, False, alpha, beta)
                        self.board[y][x].value = None
                        best_score = max(score, best_score)

                        # Alpha-beta pruning
                        alpha = max(alpha, best_score)
                        if beta <= alpha:
                            return best_score  # Prune remaining branches

            return best_score
        else:
            best_score = float("inf")
            for y in range(3):
                for x in range(3):
                    if self.board[y][x].value is None:
                        self.board[y][x].value = self.X
                        score = self.minimax_alpha_beta(depth + 1, True, alpha, beta)
                        self.board[y][x].value = None
                        best_score = min(score, best_score)

                        # Alpha-beta pruning
                        beta = min(beta, best_score)
                        if beta <= alpha:
                            return best_score  # Prune remaining branches

            return best_score

    def evaluate(self):
        # Check rows
        for y in range(3):
            if (
                self.board[y][0].value
                == self.board[y][1].value
                == self.board[y][2].value
                and self.board[y][0].value is not None
            ):
                return self.board[y][0].value

        # Check columns
        for x in range(3):
            if (
                self.board[0][x].value
                == self.board[1][x].value
                == self.board[2][x].value
                and self.board[0][x].value is not None
            ):
                return self.board[0][x].value

        # Check diagonals
        if (
            self.board[0][0].value == self.board[1][1].value == self.board[2][2].value
            and self.board[0][0].value is not None
        ):
            return self.board[0][0].value

        if (
            self.board[0][2].value == self.board[1][1].value == self.board[2][0].value
            and self.board[0][2].value is not None
        ):
            return self.board[0][2].value

        # Check for tie
        for y in range(3):
            for x in range(3):
                if self.board[y][x].value is None:
                    return None  # Game still ongoing

        # If we reach here, it's a tie
        return self.Tie

    def check_winner(self):
        """Check if there is a winner or a tie and update self.winner"""
        # Check rows
        for y in range(3):
            if (
                self.board[y][0].value is not None
                and self.board[y][0].value
                == self.board[y][1].value
                == self.board[y][2].value
            ):
                self.winner = self.current_player
                return True

        # Check columns
        for x in range(3):
            if (
                self.board[0][x].value is not None
                and self.board[0][x].value
                == self.board[1][x].value
                == self.board[2][x].value
            ):
                self.winner = self.current_player
                return True

        # Check diagonals
        if (
            self.board[0][0].value is not None
            and self.board[0][0].value
            == self.board[1][1].value
            == self.board[2][2].value
        ):
            self.winner = self.current_player
            return True

        if (
            self.board[0][2].value is not None
            and self.board[0][2].value
            == self.board[1][1].value
            == self.board[2][0].value
        ):
            self.winner = self.current_player
            return True

        # Check for tie
        for y in range(3):
            for x in range(3):
                if self.board[y][x].value is None:
                    return False  # Game still ongoing

        # If we reach here, it's a tie
        self.winner = self.Tie
        return True
