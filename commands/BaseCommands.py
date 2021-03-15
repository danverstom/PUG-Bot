from discord.ext.commands import Cog
from random import randint
from discord.embeds import Embed
from discord import Colour
from discord_slash.cog_ext import cog_slash
from utils.config import SLASH_COMMANDS_GUILDS
from utils.utils import create_list_pages
from database.database import get_sorted_elo


class BaseCommands(Cog, name="Base Commands"):
    """
    This category contains base commands that can be used by anyone
    """

    def __init__(self, bot):
        self.bot = bot

    @cog_slash(name="ping", description="Returns the latency of the bot",
               options=[], guild_ids=SLASH_COMMANDS_GUILDS)
    async def ping(self, ctx):
        """
        Returns the latency of the bot
        """
        await ctx.send("Pong! Bot latency: {}ms".format(round(self.bot.latency * 1000, 1)))

    @cog_slash(name="coinflip", description="a coinflip",
               options=[], guild_ids=SLASH_COMMANDS_GUILDS)
    async def coinflip(self, ctx):
        """
        Coinflip
        """
        c = randint(0, 1)
        if c == 0:
            result = "**Heads**"
        else:
            result = "**Tails**"

        await ctx.send(
            embed=Embed(title="Coinflip 🪙", description=f"You flipped {result}", color=Colour.dark_purple()))

    @cog_slash(name="leaderboard", description="Displays an ELO leaderboard",
               options=[], guild_ids=SLASH_COMMANDS_GUILDS)
    async def leaderboard(self, ctx):
        data = get_sorted_elo()
        leaderboard_entries = []
        count = 1
        for item in data:
            leaderboard_entries.append(f"**#{count}:** {item[0]} - **{item[1]}**")
            count += 1

        await create_list_pages(self.bot, ctx, "Leaderboard", leaderboard_entries, "There are no registered players",
                                elements_per_page=20,
                                thumbnails=[f"https://cravatar.eu/helmavatar/{data[0][0]}/128.png"],
                                can_be_reversed=True)

    @cog_slash(guild_ids=SLASH_COMMANDS_GUILDS, options=[])
    async def error_test_command(self, ctx):
        int("bonjour")
        await ctx.send("test")
