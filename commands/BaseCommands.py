from discord.ext.commands import Cog
from random import randint, choice
from discord.embeds import Embed
from discord import Colour
from discord_slash.cog_ext import cog_slash, manage_commands
from utils.config import SLASH_COMMANDS_GUILDS, MOD_ROLE, TIMEZONE
from utils.utils import create_list_pages, has_permissions
from database.Player import Player
from database.database import get_sorted_elo
from datetime import datetime, timedelta
from dateutil.tz import gettz


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

    @cog_slash(name="time", description="Show time", options=[], guild_ids=SLASH_COMMANDS_GUILDS)
    async def time(self, ctx):
        tz = gettz(TIMEZONE) 
        time = datetime.now(tz)
        await ctx.send(f"System time is {time.strftime('%H:%M:%S')}. Your time is <t:{int(time.timestamp())}:T>")

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


    @cog_slash(name="schedule", description="Create a quick copypaste schedule message",
               options=[manage_commands.create_option(name="alternation",
                                                      description="Alternate between late/early times",
                                                      option_type=3, required=False,
                                                      choices=["EarlyMon", "LateMon"])],
               guild_ids=SLASH_COMMANDS_GUILDS)
    async def schedule(self, ctx, alternation = "EarlyMon"):
        if not has_permissions(ctx, MOD_ROLE):
            await ctx.send("You do not have sufficient permissions to perform this command", hidden=True)
            return False
        j=0
        if alternation == "LateMon":
            j=1
        start = datetime.today() - timedelta(days=datetime.today().weekday() % 7)
        num_of_pugs = [1, 1, 1, 1, 2, 2, 2]

        early = ["2pm EST", "3pm EST", "4pm EST"]
        late = ["7pm EST", "8pm EST"]

        sched_str = ""
        sched_str += f"__**Week of {int(start.strftime('%m'))}/{int(start.strftime('%d'))}**__\n\n"
        # await ctx.send(sched_str)
        for pugs in num_of_pugs:
            if pugs == 2:
                j = 0
            for i in range(pugs):
                # message = await ctx.channel.send(
                #     f"**{start.strftime('%A')} {int(start.strftime('%m'))}/{int(start.strftime('%d'))} - {choice(early) if j % 2 == 0 else choice(late)}**")
                sched_str += f"**{start.strftime('%A')} {int(start.strftime('%m'))}/{int(start.strftime('%d'))} - {choice(early) if j % 2 == 0 else choice(late)}**\n"
                # await message.add_reaction("✅")
                j += 1
            start += timedelta(days=1)
        await ctx.send(f"Here's a copypasta of the dates\n```{sched_str}```")
