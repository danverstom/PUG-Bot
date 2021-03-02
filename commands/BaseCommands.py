from discord.ext.commands import Cog, command
from random import randint, choice
from json import load
from discord.embeds import Embed
from discord import Colour
from discord import File
from discord_slash.cog_ext import cog_slash
from discord_slash import SlashContext
from utils.config import SLASH_COMMANDS_GUILDS


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
