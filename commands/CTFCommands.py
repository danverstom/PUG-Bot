from discord.ext.commands import Cog
from discord import File, Embed, Colour
from utils.CTFGame import get_server_games, CTFGame
from utils.utils import response_embed, create_list_pages
from random import choice
from json import load, dump
from re import split
from requests import get
from discord.ext import tasks
from bs4 import BeautifulSoup
from utils.config import FORUM_THREADS_INTERVAL_HOURS, BOT_OUTPUT_CHANNEL

# Slash commands support
from discord_slash.cog_ext import cog_slash, manage_commands
from utils.config import SLASH_COMMANDS_GUILDS


class CTFCommands(Cog, name="CTF Commands"):
    """
    This category contains ctf commands that can be used by anyone
    """
    def __init__(self, bot):
        self.bot = bot
        self.bot_channel = None

    def cog_unload(self):
        self.threads_update.cancel()

    @Cog.listener()
    async def on_ready(self):
        self.threads_update.start()
        self.bot_channel = self.bot.get_channel(BOT_OUTPUT_CHANNEL)


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

    @cog_slash(name="maps", description="Lists all maps in rotation that contains the given search",
               options=[manage_commands.create_option(name="search",
                                                      description="The string to search with",
                                                      option_type=3, required=False),
                        manage_commands.create_option(name="search_2",
                                                      description="A second map to search for",
                                                      option_type=3, required=False),
                        manage_commands.create_option(name="search_3",
                                                      description="A third map to search for",
                                                      option_type=3, required=False)
                        ], guild_ids=SLASH_COMMANDS_GUILDS)
    async def maps(self, ctx, search="", search_2="", search_3=""):
        """
        Finds all maps in rotation that contains the input
        """
        with open("utils/maps.json") as file:
            maps = load(file)
        if search:
            list_maps = [(map_name, maps[map_name]) for map_name in list(maps.keys()) if
                         search.lower() in map_name.lower() or search_2.lower() in map_name.lower()
                         or search_3.lower() in map_name.lower()]
        else:
            list_maps = list(maps.items())

        map_str = list()

        for (map_name, map_id) in list_maps:
            map_str.append(f"[{map_name}](https://www.brawl.com/games/ctf/maps/{map_id}) ({map_id})")

        if search_2:
            map_str.append(f"\n*For match server:*\n`{' '.join(str(item[1]) for item in list_maps)}`")

        await create_list_pages(self.bot, ctx, "Maps Found:", map_str, "No Maps were found")

    @cog_slash(name="stats", description="Gets most recent stats from match 1 and 2",
               guild_ids=SLASH_COMMANDS_GUILDS, options=[])
    async def stats(self, ctx):
        """
        Gets most recent stats from match 1 and 2
        """
        match_1 = get_server_games("1.ctfmatch.brawl.com")
        match_2 = get_server_games("2.ctfmatch.brawl.com")

        with open("utils/maps.json") as file:
            maps = load(file)

        embed = Embed(title="Match Stats", color=Colour.dark_purple())
        if match_1:
            embed_1_value = []
            index = min(3, len(match_1))
            for i in range(index):
                game = CTFGame(match_1[i])
                if game.mvp:
                    embed_1_value.append(
                        f":map: [{game.map_name}](https://www.brawl.com/games/ctf/maps/{maps[game.map_name]}) | :trophy: [{game.mvp}](https://www.brawl.com/players/{game.mvp})")
                else:
                    embed_1_value.append(f":map: [{game.map_name}](https://www.brawl.com/games/ctf/maps/{maps[game.map_name]}) | :trophy: **No One :(**")
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
                        f":map: [{game.map_name}](https://www.brawl.com/games/ctf/maps/{maps[game.map_name]}) | :trophy: [{game.mvp}](https://www.brawl.com/players/{game.mvp})")
                else:
                    embed_2_value.append(f":map: [{game.map_name}](https://www.brawl.com/games/ctf/maps/{maps[game.map_name]}) | :trophy: **No One :(**")
                embed_2_value.append(
                    f":chart_with_upwards_trend: [Stats](https://www.brawl.com/games/ctf/lookup/{game.game_id})")
                embed_2_value.append("")
            embed.add_field(name="__Match 2__", value="\n".join(embed_2_value), inline=False)

        if not embed.fields:
            await response_embed(ctx, "No Games Found", "There are no match games in the past 10 games played.")
        else:
            await ctx.send(embed=embed)

    @tasks.loop(hours=FORUM_THREADS_INTERVAL_HOURS)
    async def threads_update(self):
        #await self.bot_channel.send("hi jus checking if it works bye") #TODO: Have an announcement when team sizes change (scuffed roster moves)
        url = get('https://www.brawl.com/forums/299/')
        page = BeautifulSoup(url.content, features="html.parser")

        teams_threads = {}

        for thread in page.find_all("ol", class_="discussionListItems"):
            for thread in thread.find_all("li"):
                team_titles = thread.find("div", class_="titleText")
                info = team_titles.find('a', class_="PreviewTooltip")
                author = team_titles.find('a', class_="username")
                img_loc = thread.find('img')
                if "cravatar" in img_loc.get('src'):
                    author_avatar = f"https:{img_loc.get('src')}"
                else:
                    author_avatar = f"https://www.brawl.com/{img_loc.get('src')}"
                thread_link = f"https://www.brawl.com/{info.get('href')}"
                team_title = split("((\[|\()?[0-9][0-9]/25(\]|\))?)", info.text, 1)
                team_size = split("([0-9][0-9]/25)", info.text, 1)
                try: #this try/except could be optimized but it's only because team_title raises an error since oly does not have member count in title (will do some day)
                    print(
                        f"{team_title[0]}\nLink: {thread_link}\nMembers: {team_size[1]}\nAuthor: {author.text}\nImage: {author_avatar} \n")
                    teams_threads[team_title[0].rstrip()] = {
                        "link": thread_link,
                        "members": team_size[1],
                        "author": author.text,
                        "image": author_avatar
                    }
                except:
                    print(
                        f"{team_title[0]}\nLink: {thread_link}\nMembers: NaN\nAuthor: {author.text}\nImage: {author_avatar} \n")
                    teams_threads[team_title[0].rstrip()] = {
                        "link": thread_link,
                        "members": "NaN",
                        "author": author.text,
                        "image": author_avatar
                    }

        with open('utils/team_threads.json', 'w') as file:
            dump(teams_threads, file, indent=4)

    @cog_slash(name="threads", description="Shows team threads from the forums",
               guild_ids=SLASH_COMMANDS_GUILDS, options=[])
    async def threads(self, ctx):

        with open('utils/team_threads.json') as file:
            threads = load(file)

        teams_info = []
        for thread in threads:
            info = f"**{thread}**\n\n" \
                   f"**Author**: {threads[thread]['author']}\n" \
                   f"**Members**: {threads[thread]['members']}\n" \
                   f"**Link**: {threads[thread]['link']}\n"
            teams_info.append(info)

        await create_list_pages(self.bot, ctx, "Team threads", teams_info, "Empty :(", "\n", 1)
