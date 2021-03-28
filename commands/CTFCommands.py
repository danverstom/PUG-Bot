from discord.ext.commands import Cog
from discord import File, Embed, Colour
from utils.CTFGame import get_server_games, CTFGame
from utils.utils import response_embed, success_embed, create_list_pages
from random import choice
from json import load, dump
from re import split
from requests import get
from discord.ext import tasks
from bs4 import BeautifulSoup
from utils.config import FORUM_THREADS_INTERVAL_HOURS, BOT_OUTPUT_CHANNEL, GENERAL_CHAT, TIMEZONE
from os import path

# ss
import os
import gspread
import pandas as pd
from dateutil import parser
from datetime import datetime
from pytz import timezone

# Slash commands support
from discord_slash.cog_ext import cog_slash, manage_commands
from utils.config import SLASH_COMMANDS_GUILDS


class Match:
    def __init__(self, name, datetime, end):
        self.name = name
        self.datetime = datetime
        self.end = end

    def date(self):
        return f"{self.datetime.date()}"

    def start_time(self):
        if os.name == "nt":
            return self.datetime.strftime("%#I:%M%p")
        return self.datetime.strftime("%-I:%M%p")

    def end_time(self):
        if os.name == "nt":
            return self.end.strftime("%#I:%M%p")
        return self.end.strftime("%-I:%M%p")

    def __str__(self):
        if os.name == "nt":
            return f"**{self.name}**\n{self.datetime.strftime('%A')}, {self.datetime.strftime('%B')} {self.datetime.strftime('%#d')}\n{self.start_time()} - {self.end_time()} EST\n"
        return f"**{self.name}**\n{self.datetime.strftime('%A')}, {self.datetime.strftime('%B')} {self.datetime.strftime('%-d')}\n{self.start_time()} - {self.end_time()} EST\n"

    def __lt__(self, other):
        return self.datetime < other.datetime

    # i really didnt have to make this class


class CTFCommands(Cog, name="CTF Commands"):
    """
    This category contains ctf commands that can be used by anyone
    """

    def __init__(self, bot):
        self.bot = bot
        self.bot_channel = None
        self.general_chat = None

    def cog_unload(self):
        self.threads_update.cancel()

    @Cog.listener()
    async def on_ready(self):
        self.bot_channel = self.bot.get_channel(BOT_OUTPUT_CHANNEL)
        self.general_chat = self.bot.get_channel(GENERAL_CHAT)
        self.threads_update.start()

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

        map_str = list()

        if search:
            list_maps = [(map_name, maps[map_name]) for map_name in list(maps.keys()) if
                         search.lower() in map_name.lower()]
        else:
            list_maps = list(maps.items())

        if search_2:
            list_maps_2 = [(map_name, maps[map_name]) for map_name in list(maps.keys()) if
                           search_2.lower() in map_name.lower()]
            list_maps += list_maps_2

        if search_3:
            list_maps_3 = [(map_name, maps[map_name]) for map_name in list(maps.keys()) if
                           search_3.lower() in map_name.lower()]
            list_maps += list_maps_3

        for (map_name, map_id) in list_maps:
            map_str.append(f"[{map_name}](https://www.brawl.com/games/ctf/maps/{map_id}) ({map_id})")

        if len(list_maps) == 3:  # Shows map ids only if there are 3 results
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
        match_1.reverse()
        match_2.reverse()

        with open("utils/maps.json") as file:
            maps = load(file)

        embed = Embed(title="Match Stats", color=Colour.dark_purple())
        if match_1:
            embed_1_value = []
            index = min(3, len(match_1))
            for i in range(index):
                game = CTFGame(match_1[i])
                if game.map_name in maps.keys():
                    map_str = f":map: **[{game.map_name}](https://www.brawl.com/games/ctf/maps/{maps[game.map_name]})**"
                else:
                    map_str = f":map: **{game.map_name}**"
                if game.mvp:
                    mvp_str = f":trophy: **[{game.mvp}](https://www.brawl.com/players/{game.mvp})**"
                else:
                    mvp_str = f":trophy: **No One :(**"
                embed_1_value.append(f"{map_str} | {mvp_str}")
                embed_1_value.append(
                    f":chart_with_upwards_trend: **[Stats](https://www.brawl.com/games/ctf/lookup/{game.game_id})**")
                embed_1_value.append("")
            embed.add_field(name="__Match 1__", value="\n".join(embed_1_value), inline=False)
        if match_2:
            embed_2_value = []
            index = min(3, len(match_2))
            for i in range(index):
                game = CTFGame(match_2[i])
                if game.map_name in maps.keys():
                    map_str = f":map: **[{game.map_name}](https://www.brawl.com/games/ctf/maps/{maps[game.map_name]})**"
                else:
                    map_str = f":map: **{game.map_name}**"
                if game.mvp:
                    mvp_str = f":trophy: **[{game.mvp}](https://www.brawl.com/players/{game.mvp})**"
                else:
                    mvp_str = f":trophy: **No One :(**"
                embed_2_value.append(f"{map_str} | {mvp_str}")
                embed_2_value.append(
                    f":chart_with_upwards_trend: **[Stats](https://www.brawl.com/games/ctf/lookup/{game.game_id})**")
                embed_2_value.append("")
            embed.add_field(name="__Match 2__", value="\n".join(embed_2_value), inline=False)

        if not embed.fields:
            await response_embed(ctx, "No Games Found", "There are no match games in the past 10 games played.")
        else:
            await ctx.send(embed=embed)

    async def rosters_comparison(self, old_threads, new_threads): #Compares old and new forum threads (team sizes)
        changes = ""
        for thread in old_threads:
            if thread not in new_threads:
                changes += f"---{thread}\n\n"

        for thread in new_threads:
            if thread in old_threads:
                if new_threads[thread]['members'] != old_threads[thread]['members']:
                    new_size = int(new_threads[thread]['members'].split("/")[0])
                    old_size = int(old_threads[thread]['members'].split("/")[0])
                    if new_size > old_size:
                        changes += (
                            f"🟢 **{thread}:** {old_threads[thread]['members']} -> {new_threads[thread]['members']} (**+{new_size - old_size}**)\n\n")
                    else:
                        changes += (
                            f"🔴 **{thread}:** {old_threads[thread]['members']} -> {new_threads[thread]['members']} (**{new_size - old_size}**)\n\n")
            else:
                changes += f"+++{thread}\n\n"
        if changes:
            embed = Embed(title="Roster Changes", description=changes, color=Colour.dark_purple())
            message = await self.general_chat.send(embed=embed)
            return message
        else:
            print(f"No roster moves in the last {FORUM_THREADS_INTERVAL_HOURS}h")

    @tasks.loop(hours=FORUM_THREADS_INTERVAL_HOURS)
    async def threads_update(self):
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
                try:  # uhh haha not all teams have member size in title
                    team_size = team_size[1]
                except:
                    team_size = "NaN"

                teams_threads[team_title[0].rstrip()] = {
                    "link": thread_link,
                    "members": team_size,
                    "author": author.text,
                    "image": author_avatar
                }

        if path.exists('utils/team_threads.json'):
            with open('utils/team_threads.json') as file:
                old_threads = load(file)
            await self.rosters_comparison(old_threads, teams_threads)

        with open('utils/team_threads.json', 'w') as file:
            dump(teams_threads, file, indent=4)

    @cog_slash(name="threads", description="Shows team threads from the forums",
               guild_ids=SLASH_COMMANDS_GUILDS,
               options=[manage_commands.create_option(
                   name="search_term", description="The team thread you would like to search for",
                   option_type=3, required=False
               )])
    async def threads(self, ctx, search_term=None):

        with open('utils/team_threads.json') as file:
            threads = load(file)

        teams_info = []
        thumbnails = []
        if search_term:
            filtered_thread_names = []
            count = 0
            for thread in threads:
                if search_term.lower() in thread.lower():
                    filtered_thread_names.append(thread)
                    count += 1
            for thread in filtered_thread_names:
                info = f"**{thread}**\n\n" \
                       f"**Author**: {threads[thread]['author']}\n" \
                       f"**Members**: {threads[thread]['members']}\n" \
                       f"**Link**: {threads[thread]['link']}\n"
                teams_info.append(info)
                thumbnails.append(threads[thread]['image'])

            await create_list_pages(self.bot, ctx, "Team threads", teams_info, "No results", "\n", 1,
                                    thumbnails=thumbnails)
        else:
            for thread in threads:
                info = f"**{thread}**\n\n" \
                       f"**Author**: {threads[thread]['author']}\n" \
                       f"**Members**: {threads[thread]['members']}\n" \
                       f"**Link**: {threads[thread]['link']}\n"
                teams_info.append(info)
                thumbnails.append(threads[thread]['image'])

            await create_list_pages(self.bot, ctx, "Team threads", teams_info, "Empty :(", "\n", 1,
                                    thumbnails=thumbnails)

    @cog_slash(name="ss", description="Shows upcoming matches", guild_ids=SLASH_COMMANDS_GUILDS,
               options=[
                   manage_commands.create_option(
                       name="match",
                       description="Which match server to view",
                       option_type=3,
                       required=False,
                       choices=[
                           manage_commands.create_choice(
                               name="Match 1",
                               value="1"
                           ),
                           manage_commands.create_choice(
                               name="Match 2",
                               value="2")]
                   )
               ]
               )
    async def ss(self, ctx, server="1"):
        gc = gspread.service_account(filename='utils/service_account.json')
        if server == "1":
            values = gc.open_by_key("1CrQOxzaXC6iSjwZwQvu6DNIYsCDg-uQ4x5UiaWLHzxg").worksheet("Upcoming Matches").get(
                "c10:w59")
        else:
            values = gc.open_by_key("1CrQOxzaXC6iSjwZwQvu6DNIYsCDg-uQ4x5UiaWLHzxg").worksheet(
                "Upcoming Matches (Server 2)").get("c10:w59")

        df = pd.DataFrame.from_records(values)
        row = df.loc[0]  
        res = None
        tz = timezone(TIMEZONE) 
        if os.name == "nt":
            res = row[row == (datetime.now(tz).strftime("%#m/%d/%Y"))].index
        else:
            res = row[row == (datetiome.now(tz).strftime(
                "%-m/%d/%Y"))].index  

        matches = []

        days = df.iloc[0:2, res[0]:22] #if we wanted to make SS past, it would be here
        df2 = df.iloc[2:, res[0]:22] #and here

        days.iloc[0, :] = days.iloc[0, :] + " " + days.iloc[1, :] #combine days and dates into one row
        days = days.iloc[0] #change dataframe into just that one row with days/dates

        melted_df = pd.melt(df2) #"melt" all columns into one single column (one after another)
        melted_df = melted_df.replace(to_replace=days.index, value=days) #replace numerical index of days to actual date strings

        time_column = pd.concat([df.iloc[2:, 0]]*len(df2.columns)).reset_index(drop=True) #repeat the times

        melted_df.iloc[:, 0] = melted_df.iloc[:, 0] + " " + time_column #then combine days+date with time, so our dataframe has columns of [Day, date, time], and [matchname] 
        melted_df = melted_df.replace(["", None], "#~#~#").replace("^", None).ffill() # 'detect' all events. THIS INCLUDES TIMES WHERE THERES NO MATCHES! 
        grouped_df = melted_df.groupby([(melted_df.iloc[:, 1] != melted_df.iloc[:, 1].shift()).cumsum()]) # group by consecutive values
        #grouped_df = grouped_df #add .filter(lambda x: x.iloc[0, 1] != "#~#~#") on the end of this line to get 1 dataframe of all valid matches!

        for group_index, group_df in grouped_df: #got it down to one iteration of just detected events
            #GROUP_INDEX/GROUP_DF REPRESENTS ALL THE GROUPS DETECTED IN THE SS! EVEN EMPTY EVENTS! (where nothing is happening)
            if group_df.iloc[0, 1] == "#~#~#": continue #SO WE REJECT THE EMPTY EVENTS
            
            match_df = group_df.iloc[[0, -1]] 
            start_time = match_df.iloc[0][0].split(" - ")[0]
            index = match_df.index[1]+1
            if index == len(melted_df.index): #case for the last day, last time on SS
                index = match_df.index[1]
            end_time = melted_df.iloc[index][0].split(" - ")[0]
            name = match_df.iloc[1][1]

            start = parser.parse(start_time, tzinfos={"EST": "UTC-4"}) 
            end = parser.parse(end_time, tzinfos={"EST": "UTC-4"}) 

            matches.append(Match(name, start, end))
        matches.sort()

        if matches:
            return await success_embed(ctx, "\n".join(list(map(lambda x: str(x), matches[:7]))))  # lambda
        await success_embed(ctx, "No upcoming matches")
