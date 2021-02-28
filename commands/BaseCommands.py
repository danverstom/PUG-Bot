from discord.ext.commands import Cog, command
from random import randint, choice
from json import load
from discord.embeds import Embed
from discord import Colour
from discord import File


class BaseCommands(Cog, name="Base Commands"):
    """
    This category contains base commands that can be used by anyone
    """

    def __init__(self, bot):
        self.bot = bot

    @command()
    async def ping(self, ctx):
        """
        Returns the latency of the bot
        """
        await ctx.send("Pong! Bot latency: {}ms".format(round(self.bot.latency * 1000, 1)))

    @command()
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

    @command()
    async def rngmap(self, ctx):
        """
        Picks a random map out of a preset map pool
        """
        with open("utils/rng_maps.json") as file:
            maps = load(file)
        random_map = choice(list(maps.keys()))

        file = File(f"C:\Py PUG Bot\PUG-Bot\IDs\{maps[random_map]}.png", filename=f"{maps[random_map]}.png") #Reminder to change path here
        embed = Embed(title="RNG Map",
                      description=f"You will be playing [**{random_map}**](https://www.brawl.com/games/ctf/maps/{maps[random_map]}) ({maps[random_map]})", color=Colour.dark_purple())
        embed.set_image(url=f"attachment://{maps[random_map]}.png")
        await ctx.send(file=file, embed=embed)

