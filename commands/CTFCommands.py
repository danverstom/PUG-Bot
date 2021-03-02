from discord.ext.commands import Cog, command
from discord import File, Embed, Colour
from utils.ctf_stats import get_server_games, CTFGame
from utils.utils import response_embed
from random import choice
from json import load

# Slash commands support
from discord_slash.cog_ext import cog_slash, manage_commands
from utils.config import SLASH_COMMANDS_GUILDS
from discord_slash import SlashContext


class CTFCommands(Cog, name="CTF Commands"):
    @cog_slash(name="rngmap", description="Picks a random map out of a preset map pool",
               guild_ids=SLASH_COMMANDS_GUILDS, options=[])
    async def rngmap(self, ctx: SlashContext):
        """
        Picks a random map out of a preset map pool
        """
        with open("utils/rng_maps.json") as file:
            maps = load(file)
        random_map = choice(list(maps.keys()))

        file = File(f"assets/map_screenshots/{maps[random_map]}.jpg", filename=f"{maps[random_map]}.png")
        embed = Embed(title="RNG Map",
                      description=f"You will be playing [{random_map}](https://www.brawl.com/games/ctf/maps/{maps[random_map]}) ({maps[random_map]})",
                      color=Colour.dark_purple())
        embed.set_image(url=f"attachment://{maps[random_map]}.png")
        await ctx.send(file=file, embed=embed)

    @cog_slash(name="stats", description="Gets most recent stats from match 1 and 2",
               guild_ids=SLASH_COMMANDS_GUILDS, options=[])
    async def stats(self, ctx: SlashContext):
        """
        Gets most recent stats from match 1 and 2
        """
        match_1 = get_server_games("1.ctfmatch.brawl.com")
        match_2 = get_server_games("2.ctfmatch.brawl.com")

        embed = Embed(title="Match Stats", color=Colour.dark_purple())
        if match_1:
            embed_1_value = []
            index = min(3, len(match_1))
            for i in range(index):
                game = CTFGame(match_1[i])
                if game.mvp:
                    embed_1_value.append(
                        f":map: **{game.map_name}** | :trophy: [{game.mvp}](https://www.brawl.com/players/{game.mvp})")
                else:
                    embed_1_value.append(f":map: **{game.map_name}** | :trophy: **No One :(**")
                embed_1_value.append(
                    f":chart_with_upwards_trend: [Stats](https://www.brawl.com/games/ctf/lookup/{game.game_id})")
                embed_1_value.append("")
            embed.add_field(name="__Match 1__", value="\n".join(embed_1_value), inline=False)
        if match_2:
            embed_2_value = []
            index = min(3, len(match_2))
            for i in range(index):
                game = CTFGame(match_2[i])
                if game.mvp:
                    embed_2_value.append(
                        f":map: **{game.map_name}** | :trophy: [{game.mvp}](https://www.brawl.com/players/{game.mvp})")
                else:
                    embed_2_value.append(f":map: **{game.map_name}** | :trophy: **No One :(**")
                embed_2_value.append(
                    f":chart_with_upwards_trend: [Stats](https://www.brawl.com/games/ctf/lookup/{game.game_id})")
                embed_2_value.append("")
            embed.add_field(name="__Match 2__", value="\n".join(embed_2_value), inline=False)

        if not embed.fields:
            await response_embed(ctx, "No Games Found", "There are no match games in the past 10 games played.")
        else:
            await ctx.send(embed=embed)
