from discord.ext.commands import Cog
from random import randint
from discord.embeds import Embed
from discord import Colour
from discord_slash.cog_ext import cog_slash, manage_commands
from utils.config import SLASH_COMMANDS_GUILDS
from utils.utils import create_list_pages
from database.Player import Player
from database.database import get_sorted_elo
from datetime import datetime
from pytz import timezone


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

    @cog_slash(name="time", description="Show system time", options=[], guild_ids=SLASH_COMMANDS_GUILDS)
    async def time(self, ctx):
        tz = timezone('US/Eastern') 
        time = datetime.now(tz)
        await ctx.send(f"The time is {time.strftime('%H:%M:%S')}")

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
               options=[manage_commands.create_option(name="role",
                                                      description="Filter leaderboard by role",
                                                      option_type=8, required=False)], guild_ids=SLASH_COMMANDS_GUILDS)
    async def leaderboard(self, ctx, role=None):
        player = Player.exists_discord_id(ctx.author.id)
        data = get_sorted_elo()
        leaderboard_entries = []
        count = 1
        if role:
            data = list(filter(lambda item: item[2] in [member.id for member in ctx.guild.members], data))
            data = list(filter(lambda item: role in ctx.guild.get_member(item[2]).roles, data))
        for item in data:
            if player:
                if player.minecraft_username == item[0]:
                    leaderboard_entries.append(f"\n> **#{count}:** `{item[0]}` - **{item[1]}**\n")
                    count += 1
                    continue
            leaderboard_entries.append(f"**#{count}:** `{item[0]}` - **{item[1]}**")
            count += 1
        title = "Leaderboard"
        no_reg_desc = "There are no registered players"
        if role:
            title += f" | {role.name}"
            no_reg_desc = "There are no registered players with that role"
        await create_list_pages(self.bot, ctx, title, leaderboard_entries, no_reg_desc,
                                elements_per_page=20,
                                thumbnails=[f"https://cravatar.eu/helmavatar/{data[0][0]}/128.png"] if data else [],
                                can_be_reversed=True)

    @cog_slash(guild_ids=SLASH_COMMANDS_GUILDS, options=[])
    async def error_test_command(self, ctx):
        int("bonjour")
        await ctx.send("test")
