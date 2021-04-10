from discord.ext.commands import Cog
from discord.ext import tasks
from discord import File, Embed, Colour
from utils.stat_util import *
from utils.plot_utils import *
from utils.utils import *
import logging
from mojang import MojangAPI

# Slash commands support
from discord_slash.cog_ext import cog_slash, manage_commands
from utils.config import SLASH_COMMANDS_GUILDS


class LifetimeStatsGame(Cog, name="CTF Commands"):
    """
    A game where you guess the player from plots of the stats
    """
    def __init__(self, bot):
        self.bot = bot
        self.bot_channel = None
        self.general_chat = None
        self.in_progress = False

    @staticmethod
    async def comp_playtime_pie(ign):
        data = await get_lifetime_stats(ign)
        if data:
            mode = "competitive"
            if not len(data[mode].keys()) > 0:
                return False
            sizes = [int(data[mode][key]["playtime"]) for key in data[mode].keys()]
            avg_size = sum(sizes) / len(sizes)
            labels = [(key.title() if float(data[mode][key]["playtime"]) > avg_size else "") for key in data[mode].keys()]
            # TODO: sort these lists to make the pie chart look better
            data_stream = pie_chart(labels, sizes, explode=[0.1 if label else 0 for label in labels],
                                    title="Playtime by class")
            data_stream.seek(0)
            chart_file = File(data_stream, filename="pie_chart.png")
            return chart_file
        else:
            return False

    @cog_slash(guild_ids=SLASH_COMMANDS_GUILDS)
    async def gameofstats(self, ctx):
        """Compete with other members to guess the player from their stats"""
        if self.in_progress:
            await error_embed(ctx, "There is already a game in progress")
            return
        self.in_progress = True
        winners = []
        attempts = 0
        await ctx.send("Welcome to Game of Stats! Respond with `>[IGN]` to guess the player. Old names work too.")
        for round_num in range(1, 6):
            while True:
                random_player = Player.fetch_random_player()
                random_ign = random_player.minecraft_username
                logging.info(f"Random IGN generated: {random_ign}")
                uuid = random_player.minecraft_id
                names_dict = MojangAPI.get_name_history(uuid)
                all_names = [item["name"].lower() for item in names_dict]
                logging.info(all_names)
                pie_file = await self.comp_playtime_pie(random_ign)
                if pie_file:
                    await ctx.send(content=f"Round {round_num}:", file=pie_file)
                    guessed = False
                    while not guessed:
                        response = await self.bot.wait_for("message")
                        content = response.content.lower()
                        if content.startswith(">"):
                            logging.info(content.strip(">"))
                            logging.info(all_names)
                            if content.strip(">") in all_names:
                                await response.add_reaction("✅")
                                await response.reply(f"You guessed correctly! ({random_ign})")
                                winners.append(response.author)
                                guessed = True
                            else:
                                await response.add_reaction("❌")
                    break
                else:
                    if attempts > 5:
                        ctx.send("There were errors getting stats or generating pie charts")
                        return
                    attempts += 1
                    continue
        await ctx.send("Game finished! Congratulations to the winners - " +
                       " ".join(list(set(winner.mention for winner in winners))))
        self.in_progress = False


