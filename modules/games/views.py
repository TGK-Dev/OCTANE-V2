import discord
from discord.ui import View, Button
import random


class MinesweeperButton(Button):
    def __init__(self, x, y):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            emoji="<:blank:965161644206473216>",
            row=y,
        )
        self.x = x
        self.y = y
        self.is_mine = False
        self.is_revealed = False
        self.adjacent_mines = 0


class Minesweeper(View):
    def __init__(self, player: discord.Member):
        super().__init__(timeout=180)  # 3 minutes timeout
        self.player = player
        self.board_size = 5
        self.num_mines = 5
        self.game_over = False
        self.remaining_safe_cells = self.board_size * self.board_size - self.num_mines
        self.board = [
            [None for _ in range(self.board_size)] for _ in range(self.board_size)
        ]

        # Initialize the board
        self._initialize_board()

    async def interaction_check(self, interaction):
        if interaction.user != self.player:
            await interaction.response.send_message(
                "This game is not for you!", ephemeral=True
            )
            return False
        return True

    def _initialize_board(self):
        # Create buttons
        for y in range(self.board_size):
            for x in range(self.board_size):
                button = MinesweeperButton(x, y)
                button.callback = self.make_callback(x, y)
                self.board[y][x] = button
                self.add_item(button)

        # Place mines
        self._place_mines()

        # Calculate adjacent mines
        self._calculate_adjacent_mines()

    def make_callback(self, x, y):
        async def button_callback(interaction):
            await self._handle_click(interaction, x, y)

        return button_callback

    async def _handle_click(self, interaction, x, y):
        button = self.board[y][x]

        if self.game_over or button.is_revealed:
            await interaction.response.defer()
            return

        # Reveal the cell
        win = self._reveal_cell(x, y)

        # Update the message with the current game state
        if self.game_over:
            if win:
                embed = discord.Embed(
                    title="🎮 Minesweeper: Victory!",
                    description="🎉 You Win! All safe cells revealed!",
                    color=discord.Color.green(),
                )
            else:
                embed = discord.Embed(
                    title="🎮 Minesweeper: Game Over",
                    description="💥 Game Over! You hit a mine!",
                    color=discord.Color.red(),
                )
            embed.set_footer(text=f"Game played by {self.player.display_name}")
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            # Game continues
            embed = discord.Embed(
                title="🎮 Minesweeper",
                description="Click the buttons to reveal cells. Avoid the mines!",
                color=discord.Color.blue(),
            )
            embed.set_footer(text=f"Game played by {self.player.display_name}")
            await interaction.response.edit_message(embed=embed, view=self)

    def _place_mines(self):
        # Create a flat list of all positions
        positions = [
            (x, y) for y in range(self.board_size) for x in range(self.board_size)
        ]
        # Randomly select positions for mines
        mine_positions = random.sample(positions, self.num_mines)

        # Place mines
        for x, y in mine_positions:
            self.board[y][x].is_mine = True

        # Debug: Print mine locations in terminal
        print("=== MINESWEEPER DEBUG: MINE LOCATIONS ===")
        board_repr = []
        for y in range(self.board_size):
            row = []
            for x in range(self.board_size):
                if self.board[y][x].is_mine:
                    row.append("💣")
                else:
                    row.append("⬜")
            board_repr.append(" ".join(row))
        print("\n".join(board_repr))
        print("=======================================")

    def _calculate_adjacent_mines(self):
        for y in range(self.board_size):
            for x in range(self.board_size):
                if not self.board[y][x].is_mine:
                    self.board[y][x].adjacent_mines = self._count_adjacent_mines(x, y)

    def _count_adjacent_mines(self, x, y):
        count = 0
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.board_size and 0 <= ny < self.board_size:
                    if self.board[ny][nx].is_mine:
                        count += 1
        return count

    def _disable_all_buttons(self):
        # Disable all buttons when the game ends
        for y in range(self.board_size):
            for x in range(self.board_size):
                button = self.board[y][x]
                button.disabled = True

                # Skip buttons that already have flags (from winning)
                if button.label == "🚩":
                    button.emoji = None
                    continue

                # Ensure all buttons have a valid label when disabled
                if button.emoji == "<:blank:965161644206473216>":
                    # Remove the emoji and set an appropriate label
                    button.emoji = None
                    if button.is_mine:
                        button.label = "💣"
                    elif button.adjacent_mines > 0:
                        button.label = str(button.adjacent_mines)
                    else:
                        # Keep the blank emoji for cells with no adjacent mines
                        button.emoji = "<:blank:965161644206473216>"
                        button.label = None

    def _reveal_all_mines(self):
        for y in range(self.board_size):
            for x in range(self.board_size):
                button = self.board[y][x]
                if button.is_mine:
                    button.style = discord.ButtonStyle.danger
                    button.emoji = None
                    button.label = "💣"
                # Ensure all non-mine cells have a valid label too
                elif not button.is_revealed:
                    button.emoji = None
                    if button.adjacent_mines > 0:
                        button.label = str(button.adjacent_mines)
                    else:
                        # Use blank emoji for empty cells
                        button.emoji = "<:blank:965161644206473216>"
                        button.label = None

        # Disable all buttons when mines are revealed
        self._disable_all_buttons()

    def _reveal_cell(self, x, y):
        button = self.board[y][x]

        if button.is_revealed or self.game_over:
            return False

        button.is_revealed = True

        if button.is_mine:
            # Game over - player hit a mine
            button.style = discord.ButtonStyle.danger
            button.emoji = None
            button.label = "💣"
            self.game_over = True
            self._reveal_all_mines()
            return False

        # Not a mine, show adjacent mine count
        self.remaining_safe_cells -= 1
        button.disabled = True
        button.emoji = None  # Remove the emoji when revealing

        if button.adjacent_mines > 0:
            button.label = str(button.adjacent_mines)
            # Choose color based on number
            colors = [
                discord.ButtonStyle.primary,  # 1
                discord.ButtonStyle.success,  # 2
                discord.ButtonStyle.danger,  # 3
                discord.ButtonStyle.secondary,  # 4+
            ]
            button.style = colors[min(button.adjacent_mines - 1, 3)]
        else:
            # No adjacent mines, set blank emoji
            button.label = None
            button.emoji = "<:blank:965161644206473216>"
            button.style = discord.ButtonStyle.success

            # Auto-reveal adjacent cells with no mines
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.board_size and 0 <= ny < self.board_size:
                        if (
                            not self.board[ny][nx].is_revealed
                            and not self.board[ny][nx].is_mine
                        ):
                            self._reveal_cell(nx, ny)

        # Check for win condition
        if self.remaining_safe_cells == 0 and not self.game_over:
            self.game_over = True
            for y in range(self.board_size):
                for x in range(self.board_size):
                    if self.board[y][x].is_mine:
                        # When setting flags on mines, make sure to remove the emoji
                        self.board[y][x].emoji = None
                        self.board[y][x].label = "🚩"
                        self.board[y][x].style = discord.ButtonStyle.success

            # Disable all buttons on win
            self._disable_all_buttons()
            return True

        return False
