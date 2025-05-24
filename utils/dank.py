import discord
import re


class DonationsInfo:
    """
    A class to represent a donation.

    Attributes:
        donor (discord.Member): The member who donated.
        quantity (int): The amount of items donated.
        items (str): The items donated. If None, the donation is a currency donation.
        message (discord.Message): The message that contains the donation information.
    """

    def __init__(self, donor: discord.Member, quantity: int, items: str = None):
        self.donor = donor
        self.quantity = quantity
        self.items = items
        self.message: discord.Message = None

    def __str__(self):
        if self.items:
            return f"{self.donor} donated {self.quantity} {self.items}"
        else:
            return f"{self.donor} donated {self.quantity}"

    def format(self) -> str:
        if self.items:
            return f"`{self.quantity}x {self.items}`"
        else:
            return f"`⏣ {self.quantity:,}`"


async def get_donation_from_message(message: discord.Message) -> DonationsInfo:
    """
    Parse a message from Dank Memer and return the donation information.

    Args:
        message (discord.Message): The message to parse.

    """
    if message.author.id != 270904126974590976:
        raise ValueError("Message is not from Dank Memer")

    if len(message.embeds) == 0:
        raise ValueError("Message does not contain an embed")

    if not message.interaction:
        raise ValueError("Message doese not contain an interaction object")

    donor: discord.Member = message.interaction.user

    embed: discord.Embed = message.embeds[0]

    items = re.findall(r"\*\*(.*?)\*\*", embed.description)[0]
    if "⏣" in items:
        items = int(items.replace("⏣", "").replace(",", ""))
        return DonationsInfo(donor, items)

    else:
        emojis = list(set(re.findall(":\w*:\d*", items)))
        for emoji in emojis:
            items = items.replace(emoji, "", 100)
            items = items.replace("<>", "", 100)
            items = items.replace("<a>", "", 100)
            items = items.replace("  ", " ", 100)
        mathc = re.search(r"(\d+) (.+)", items)
        if not mathc:
            raise ValueError("Could not parse items from message")

        quantity = int(mathc.group(1))
        items = mathc.group(2)

        return DonationsInfo(donor, quantity, items)


async def calculate_payments(
    daily_payment: float, paid_amount: float, missing_payments: int
) -> dict:
    """
    Calculate if a payment is more than the required payment, if it can cover future payments, and missing payments.

    Args:
        daily_payment (float): The required daily payment.
        paid_amount (float): The amount that was paid.
        missing_payments (int): The number of days of payment that are missing.

    Returns:
        dict: A dictionary with keys 'paid_for_today', 'paid_for_future_days', 'extra_left', and 'missing_payments_covered'.
    """
    paid_for_today = paid_amount >= daily_payment
    remaining_amount = paid_amount - daily_payment if paid_for_today else 0
    missing_payments_covered = min(
        int(remaining_amount // daily_payment), missing_payments
    )
    remaining_amount -= missing_payments_covered * daily_payment
    paid_for_future_days = int(remaining_amount // daily_payment)
    extra_left = remaining_amount % daily_payment

    return {
        "paid_for_today": paid_for_today,
        "missing_payments_covered": missing_payments_covered,
        "paid_for_future_days": paid_for_future_days,
        "extra_left": extra_left,
    }