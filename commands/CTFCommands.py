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
from utils.config import FORUM_THREADS_INTERVAL_HOURS, BOT_OUTPUT_CHANNEL

#ss
import os 
import gspread
import pandas as pd
from dateutil import parser
from datetime import datetime, date
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
        

    #i really didnt have to make this class

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
                if game.mvp:
                    embed_1_value.append(
                        f":map: [{game.map_name}](https://www.brawl.com/games/ctf/maps/{maps[game.map_name]}) | :trophy: [{game.mvp}](https://www.brawl.com/players/{game.mvp})")
                else:
                    embed_1_value.append(
                        f":map: [{game.map_name}](https://www.brawl.com/games/ctf/maps/{maps[game.map_name]}) | :trophy: **No One :(**")
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
                    embed_2_value.append(
                        f":map: [{game.map_name}](https://www.brawl.com/games/ctf/maps/{maps[game.map_name]}) | :trophy: **No One :(**")
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
        # await self.bot_channel.send("hi jus checking if it works bye") #TODO: Have an announcement when team sizes change (scuffed roster moves)
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
                try:  # this try/except could be optimized but it's only because team_title raises an error since oly does not have member count in title (will do some day)
                    teams_threads[team_title[0].rstrip()] = {
                        "link": thread_link,
                        "members": team_size[1],
                        "author": author.text,
                        "image": author_avatar
                    }
                except:
                    teams_threads[team_title[0].rstrip()] = {
                        "link": thread_link,
                        "members": "NaN",
                        "author": author.text,
                        "image": author_avatar
                    }
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
                    name="Match1",
                    value="1"
                  ),
                  manage_commands.create_choice(
                    name="Match2",
                    value="2")]
                 )
               ]
               )
    async def ss(self, ctx, server = "1"):
        gc = gspread.service_account(filename='utils/service_account.json')
        if server == "1":
            values = gc.open_by_key("1CrQOxzaXC6iSjwZwQvu6DNIYsCDg-uQ4x5UiaWLHzxg").worksheet("Upcoming Matches").get("c10:w59")
        else:
            values = gc.open_by_key("1CrQOxzaXC6iSjwZwQvu6DNIYsCDg-uQ4x5UiaWLHzxg").worksheet("Upcoming Matches (Server 2)").get("c10:w59")

        df = pd.DataFrame.from_records(values)
        row = df.loc[0] #get row with the dates
        res = None
        if os.name == "nt":
            res = row[row == (date.today().strftime("%#m/%d/%Y"))].index
        else:
            res = row[row == (date.today().strftime("%-m/%d/%Y"))].index #find index of todays date, and use that index to start from
        
        
        
        matches = []
        for column in df.iloc[:, res[0] :].columns: #[:, start :] removes the first column. [rows, column]
                                               #remove time column
                                               # if we wanted to make SS past, we would change this to be df.iloc[:, 1:res[0]]
            aDay, aDate = df[column].iloc[1], df[column].iloc[0] #get day and date
            df1 = df.iloc[2:] #remove date/day rows
            day = df1[column] #we iterate through all the days
            print(df1[column])

            day1 = df1[day.astype(bool)].iloc[:, [0, column]] #Remove all cells which dont have a value in them, whilst also adding the time column to it in a new DF
            day1 = day1.replace("^", None).ffill() # Then replace all "^" with a cell that doesnt have a value
                                                   # So we can use fill forward, which changes 'Dunce ppm, ^ ^' to
                                                   # 'Dunce ppm, dunce ppm, dunce ppm'. Ez grouping
                                                   
            first = day1.groupby([column]) # then get a DF from the changes we did ^
            
            for key, item in first: #Maybe theres a way to do this without iterating at all
                                    # not smart enough to attempt it tho
                                    
                df2 = item.iloc[[0, -1]] #get the first and last items of the dataframe. This willgive the time it starts/ends
                start_time = df2[0].iloc[0].split(" - ")[0] # get the first row (which gives us start time), get the time column and get time
                end =df2[0].tail(1).index.item() # same process but for end

                if end == 49: #special case for 11:30pm. we get the next time box which is the alternate method
                    end2 = df[0][2] #get the 12am timebox
                else:
                    end2 = df[0][end+1] #otherwise get the next one along

                end2 = end2.split(" - ")[0] #Date
                start = parser.parse(" ".join([aDay, aDate, start_time]), tzinfos={"EST": "UTC-4"}) #add the day, date, and start time to get one datetime
                
                end = parser.parse(" ".join([aDay, aDate, end2]), tzinfos={"EST": "UTC-4"}) #same for the end time
                
                matches.append(Match(key, start, end)) # i made my own class but i dont think its useful, maybe someone else can shorten the code here

        matches.sort() #since we made a class of matches, we can now decide how they are compared. Check the Match class, we compare by datetimes
        if matches:
            return await success_embed(ctx, "\n".join(list(map(lambda x: str(x), matches[:7])))) #lambda
        await success_embed(ctx, "No upcoming matches")
