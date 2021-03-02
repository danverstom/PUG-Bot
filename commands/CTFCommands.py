from discord.ext.commands import Cog, command
from discord import File, Embed, Colour
from utils.ctf_stats import get_server_games, CTFGame
from utils.utils import response_embed
from random import choice
from json import load
from math import ceil
import asyncio

# Slash commands support
from discord_slash.cog_ext import cog_slash, manage_commands
from utils.config import SLASH_COMMANDS_GUILDS
from discord_slash import SlashContext


class CTFCommands(Cog, name="CTF Commands"):
    def __init__(self, bot):
        self.bot = bot

    @cog_slash(name="rngmap", description="Picks a random map out of a preset map pool",
               guild_ids=SLASH_COMMANDS_GUILDS, options=[])
    async def rngmap(self, ctx):
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
    async def stats(self, ctx):
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

    @cog_slash(name="maplist", description="List of CTF current map rotation",
               guild_ids=SLASH_COMMANDS_GUILDS, options=[])
    async def maplist(self, ctx):

        with open('utils/maps.json') as file:
            maps = load(file)

        contents = []
        elmnts = 10  # Maps per page!!
        pages = ceil(len(maps) / elmnts)
        i = 0
        page = ""
        cur_page = 1
        for map in maps:
            i += 1
            page = page + str(f'{map} ({maps[map]})\n')
            if i == elmnts:
                contents.append(page)
                page = ""
                i = 0
        contents.append(page)

        embed = Embed(title="Map List", description=contents[cur_page - 1], colour=Colour.dark_purple())
        embed.set_footer(text=f"Page {cur_page}/{pages}")
        message = await ctx.send(embed=embed)
        # getting the message object for editing and reacting

        await message.add_reaction("◀️")
        await message.add_reaction("▶️")

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["◀️", "▶️"]
            # This makes sure nobody except the command sender can interact with the "menu"

        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=60, check=check)
                # waiting for a reaction to be added - times out after x seconds, 60 in this
                # example

                if str(reaction.emoji) == "▶️" and cur_page != pages:
                    cur_page += 1
                    embed = Embed(title="Map List", description=contents[cur_page - 1],
                                  colour=Colour.dark_purple())
                    embed.set_footer(text=f"Page {cur_page}/{pages}")
                    await message.edit(embed=embed)
                    await message.remove_reaction(reaction, user)

                elif str(reaction.emoji) == "◀️" and cur_page > 1:
                    cur_page -= 1
                    embed = Embed(title="Map List", description=contents[cur_page - 1],
                                  colour=Colour.dark_purple())
                    embed.set_footer(text=f"Page {cur_page}/{pages}")
                    await message.edit(embed=embed)
                    await message.remove_reaction(reaction, user)

                else:
                    await message.remove_reaction(reaction, user)
                    # removes reactions if the user tries to go forward on the last page or
                    # backwards on the first page
            except asyncio.TimeoutError:
                await message.delete()
                break
                # ending the loop if user doesn't react after x seconds
