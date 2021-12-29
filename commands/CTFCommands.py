from discord.ext.commands import Cog
from discord import File, Embed, Colour

from database.Player import Player
from utils.CTFGame import get_server_games, CTFGame
from utils.utils import response_embed, success_embed, create_list_pages, error_embed, request_async_json, has_permissions
from random import choice, seed
from json import load, dump
from re import split
from requests import get
from discord.ext import tasks
from bs4 import BeautifulSoup
from utils.config import FORUM_THREADS_INTERVAL_HOURS, BOT_OUTPUT_CHANNEL, GENERAL_CHAT, TIMEZONE
from os import path
import aiohttp
from asyncio import sleep as async_sleep
import logging
from utils.plot_utils import *

# ss
import os
import gspread
import pandas as pd
from dateutil import parser
from dateutil.tz import gettz
from datetime import datetime

# Slash commands support
from discord_slash.cog_ext import cog_slash, manage_commands
from utils.config import SLASH_COMMANDS_GUILDS, ADMIN_ROLE


class Match:
    def __init__(self, name, datetime, end):
        self.name = name
        self.datetime = datetime
        self.end = end

    def date(self):
        return f"{self.datetime.date()}"

    def human_times(self):
        return f"{self.start_time()} - {self.end_time()} EST"

    def human_date(self):
        if os.name == "nt":
            return f"{self.datetime.strftime('%A')}, {self.datetime.strftime('%B')} {self.datetime.strftime('%#d')}"
        return f"{self.datetime.strftime('%A')}, {self.datetime.strftime('%B')} {self.datetime.strftime('%-d')}"

    def human_datetime(self):
        if os.name == "nt":
            return f"{self.name}\n{self.datetime.strftime('%A')}, {self.datetime.strftime('%B')} {self.datetime.strftime('%#d')}\n{self.start_time()} - {self.end_time()} EST\n"
        return f"{self.name}\n{self.datetime.strftime('%A')}, {self.datetime.strftime('%B')} {self.datetime.strftime('%-d')}\n{self.start_time()} - {self.end_time()} EST\n"

    def start_time(self):
        if os.name == "nt":
            return self.datetime.strftime("%#I:%M%p")
        return self.datetime.strftime("%-I:%M%p")

    def end_time(self):
        if os.name == "nt":
            return self.end.strftime("%#I:%M%p")
        return self.end.strftime("%-I:%M%p")

    def __str__(self):
        return f"{self.name}, {self.datetime}, {self.end}"
    
    def __lt__(self, other):
        return self.datetime < other.datetime

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

    @cog_slash(guild_ids=SLASH_COMMANDS_GUILDS, options=[])
    async def brawl(self, ctx):
        """
        Returns info about the players online on brawl.com
        """
        url = "https://www.brawl.com/data/playerCount.json"
        result = await request_async_json(url, content_type="application/json")
        if not result: 
            await error_embed(ctx, "Error getting data from brawl")
            return
        await response_embed(
            ctx, 
            "Brawl Player Info", 
            "\n".join(f"**{server_name.replace('_', '.')}** - {count}" 
            for server_name, count in result[1].items())
        )
        

    @cog_slash(name="rngmap", description="Picks a random map out of a preset map pool",
               guild_ids=SLASH_COMMANDS_GUILDS, options=[])
    async def rngmap(self, ctx):
        """
        Picks a random map out of a preset map pool
        """
        await ctx.defer()
        seed()
        with open("utils/rng_maps.json") as file:
            maps = load(file)
        random_map = choice(list(maps.keys()))

        file = File(f"assets/map_screenshots/{maps[random_map]}.jpg", filename=f"{maps[random_map]}.png")
        embed = Embed(title="RNG Map",
                      description=f"You will be playing [{random_map}](https://www.brawl.com/games/ctf/maps/"
                                  f"{maps[random_map]}) ({maps[random_map]})\n_(Used by {ctx.author.mention})_",
                      color=Colour.dark_purple())
        embed.set_image(url=f"attachment://{maps[random_map]}.png")
        response = await ctx.send("Grabbing a map from the pool")
        await ctx.channel.send(file=file, embed=embed)
        await response.delete()


    @cog_slash(name="maps", description="Lists all maps or searches for maps by name",
               options=[manage_commands.create_option(name="searches",
                                                      description="Separate multiple maps with commas (blackout, pagodas III)",
                                                      option_type=3, required=False),
                        manage_commands.create_option(name="rotation_maps",
                                                      description="Show all maps or rotation only (default is rotation)",
                                                      option_type=5, required=False)
                        ], guild_ids=SLASH_COMMANDS_GUILDS)
    async def maps(self, ctx, searches="", rotation_maps=True):
        """
        Lists all maps  in rotation when no searches are provided
        Searches for maps when searches are given
        """
        await ctx.defer()
        with open("utils/maps.json") as file:
            maps = load(file)
        map_str = list()
        args = list(map(lambda x: x.strip(), filter(None, searches.lower().split(","))))

        if not rotation_maps: #Merg
            with open("utils/all_maps.json") as file:
                all_maps = load(file)
                maps = {**maps, **all_maps}

        list_maps = None
        if not searches:
            list_maps = list(maps.items())
        else:
            list_maps = []
            for search in args:
                for k, v in maps.items():
                    if search in k.lower() or search in str(v):
                        if [k, v] not in list_maps: #Only adds new elements so no dupes
                            list_maps.append([k, v])

        amount = len(list_maps) #Amount of maps found

        if not list_maps: #No results
            return await error_embed(ctx,"No maps found. Did you forget to separate maps with commas (blackout, pagodas III)?")

        if len(list_maps) == 1: #Image for single search result
            map_id = list_maps[0][1]
            map_name = list_maps[0][0]

            if os.path.exists(f"assets/map_screenshots/{map_id}.jpg"):
                file = File(f"assets/map_screenshots/{map_id}.jpg", filename=f"{map_id}.png")
                embed = Embed(title="Maps Found:", description=f"[{map_name}](https://www.brawl.com/games/ctf/maps/{map_id}) ({map_id})",
                  color=Colour.dark_purple())
                embed.set_image(url=f"attachment://{map_id}.png")
                response = await ctx.send("Fetching maps...")
                await response.edit(content="Done!")
                await ctx.channel.send(embed=embed, file=file)
            else: #Handling single search results without an image
                embed = Embed(title="Maps Found:",
                              description=f"[{map_name}](https://www.brawl.com/games/ctf/maps/{map_id}) ({map_id})",
                              color=Colour.dark_purple())
                embed.set_footer(text="This map has no image yet :(")
                response = await ctx.send("Fetching maps...")
                await response.edit(content="Done!")
                await ctx.channel.send(embed=embed)
            return
        
        for (map_name, map_id) in list_maps:
            map_str.append(f"[{map_name}](https://www.brawl.com/games/ctf/maps/{map_id}) ({map_id})")
        if len(list_maps)>5: #Sort maps by name but only for >5 results otherwise match string gets scuffed
            map_str = sorted(map_str)
        if len(list_maps) <= 5 and len(list_maps) != 0:  # Shows map ids only if there are 3 results
            map_str.append(f"\n*For match server:*\n`{' '.join(str(item[1]) for item in list_maps)}`")

        await create_list_pages(self.bot, ctx, f"Maps Found ({amount}):", map_str, "No Maps were found", random_item=True)


    @cog_slash(name="stats", description="Gets most recent stats from match 1 and 2",
               guild_ids=SLASH_COMMANDS_GUILDS, options=[])
    async def stats(self, ctx):
        """
        Gets most recent stats from match 1 and 2
        """
        await ctx.defer()
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
        #TODO: Handle error for when teams change their threads titles
        old_links = {old_threads[old_key]["link"]: old_key for old_key in old_threads.keys()}
        new_links = {new_threads[new_key]["link"]: new_key for new_key in new_threads.keys()}

        disjunct_union = set(old_links.keys()) ^ set(new_links.keys())

        for disjunct in disjunct_union:
            if disjunct in old_links:
                changes += f"🔴 **{old_links[disjunct]}** has disbanded.\n\n"
            else:
                changes += f"🟢 **{new_links[disjunct]}** is now official.\n\n"

        for o_key in old_threads.keys():
            for n_key in new_threads.keys():
                if o_key != n_key:
                    continue
                if new_threads[n_key]['members'] != old_threads[o_key]['members']:
                    new_size = int(new_threads[n_key]['members'].split("/")[0])
                    old_size = int(old_threads[o_key]['members'].split("/")[0])
                    if new_size > old_size:
                        changes += (
                            f"🟢 **{o_key}:** {old_threads[o_key]['members']} -> {new_threads[n_key]['members']} (**+{new_size - old_size}**)\n\n")
                    else:
                        changes += (
                            f"🔴 **{n_key}:** {old_threads[o_key]['members']} -> {new_threads[n_key]['members']} (**{new_size - old_size}**)\n\n")

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
                team_title = split("((\[|\()\d{1,3}/\d{1,3}(\]|\))?)", info.text, 1)

                team_size = split("(\d{1,3}/\d{1,3})", info.text, 1)
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

    @cog_slash(name="ss", description="Shows upcoming matches", guild_ids=SLASH_COMMANDS_GUILDS)
    async def ss(self, ctx):
        await ctx.defer()
        gc = gspread.service_account(filename='utils/service_account.json')
        worksheet1 = gc.open_by_key("1CrQOxzaXC6iSjwZwQvu6DNIYsCDg-uQ4x5UiaWLHzxg").worksheet("Upcoming Matches")
        worksheet2 = gc.open_by_key("1CrQOxzaXC6iSjwZwQvu6DNIYsCDg-uQ4x5UiaWLHzxg").worksheet("Upcoming Matches (Server 2)")
        matchservers = {"1": worksheet1, "2": worksheet2} 
        matches = []
        string_list = []
        tbd_list = []
        for match, values in matchservers.items():
            df = pd.DataFrame.from_records(values.get()) 
            df = df.iloc[9:, 2:].reset_index(drop=True) 
            df.columns = range(df.shape[1]) #reset column index

            row = df.loc[0]
            end_index = row[row == "TBD"].index #find the end index (either TBD or latest date). incase 
                                                #mods decide to just add days to the ss instead of replacing dates
            if end_index.empty: #no tbd section, u never know 
                end_date = [x for x in reversed(list(row.array)) if len(x.split("/")) == 3] #it works
                end_index = row[row == end_date[0]].index +1 #maybe TBD is renamed? if deleted this breaks
            else:
                tbd_column = df.iloc[2:, end_index[0]] 
                [tbd_list.append(f"**{x}** *(Match {match})*") for x in tbd_column if (x != None) and (x != "")]

            tz = gettz(TIMEZONE)
            datetime_now = datetime.now(tz)
            start_index = None
            no_pad = "-"
            if os.name == "nt":
                no_pad = "#"
            start_index = row[row == (datetime_now.strftime(f"%{no_pad}m/%{no_pad}d/%Y"))].index

            
            if start_index.empty: #todays date not found. We need to add new days
                number_of_days = len([x for x in row.array if len(x.split("/")) == 3]) 
                excel_col_name = lambda n: '' if n <= 0 else excel_col_name((n - 1) // 26) + chr((n - 1) % 26 + ord('A')) #google solution TY devon
                new_datetimes = pd.date_range(start=datetime_now, periods=number_of_days, freq="D")
                new_dates = [d.strftime(f"%{no_pad}m/%{no_pad}d/%{no_pad}Y") for d in new_datetimes] #"mm/dd/yy" no padding
                new_days = [d.strftime("%A") for d in new_datetimes] #%A is date full name E.g "Sunday"
                last_letter = excel_col_name(number_of_days+3) #+3 to account for starting at D
                cell_list = values.range(f"D10:{last_letter}59")
                for cell in cell_list:
                    if cell.row == 10: 
                        cell.value = new_dates[cell.col -4] #this'll break if they ever remove the
                    elif cell.row == 11: 
                        cell.value = new_days[cell.col -4] #hidden columns A and B
                    else:
                        cell.value = ""
                values.update_cells(cell_list)
                values.format(f"D12:{last_letter}59", {'backgroundColor': {"red": 1.0, "green": 1.0, "blue": 1.0} })
                continue

            days = df.iloc[0:2, start_index[0]:end_index[0]] 
            df2 = df.iloc[2:, start_index[0]:end_index[0]] 

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

                start = parser.parse(start_time, tzinfos={"EST": tz})
                end = parser.parse(end_time, tzinfos={"EST": tz})

                matches.append(Match(f"**{name}** *(Match {match})*", start, end))
        matches.sort()

        matches = list(filter(lambda x: datetime_now.time() < x.end.time() or datetime_now.date() != x.end.date(), matches))
        for match in matches:
            if match.datetime < datetime_now < match.end:
                string_list.append(f"> {match.name} ***(Ongoing)***\n> {match.human_date()}\n> {match.human_times()}\n")
            #maybe add func to match to see duration
            #then add time until the match to matches under 12/24h away
            else:
                string_list.append(f"{match.name}\n{match.human_date()}\n{match.human_times()}\n")
        if tbd_list:
            tbd_list.insert(0, "**TBD Section**")
            [string_list.append(x) for x in tbd_list]
        return await create_list_pages(self.bot, ctx, f"Matches Found", string_list, "No matches found :(", "\n", 5)  # lambda

    @cog_slash(guild_ids=SLASH_COMMANDS_GUILDS, options=[
        manage_commands.create_option(name="ign", description="The ign of the player you would like to search for",
                                      required=False, option_type=3),
        manage_commands.create_option(name="mode", description="Whether to look for stats in casual or competitive",
                                      required=False, option_type=3, choices=[
                manage_commands.create_choice(name="Competitive", value="competitive"),
                manage_commands.create_choice(name="Casual", value="casual")])
    ])
    async def playerstats(self, ctx, ign=None, mode="competitive"):
        """Gets player stats using 915's stats website"""
        if not ctx.responded:
            await ctx.defer()
        get_player_id_url = "https://by48xt0cuf.execute-api.us-east-1.amazonaws.com/default/request-player?name={}"
        stats_from_id_url = "https://by48xt0cuf.execute-api.us-east-1.amazonaws.com/default/request-player?id={}"
        new_player_request_url = "https://qe824lieck.execute-api.us-east-1.amazonaws.com/default/new-player?id={}"
        if ign:
            username = ign
        else:
            player = Player.exists_discord_id(ctx.author.id)
            if player:
                username = player.minecraft_username
            else:
                username = None
        if not username:
            await error_embed(ctx, "Please input a player or `/register` to get your own stats")
            return
        response = await request_async_json(get_player_id_url.format(username), 'text/plain')
        if response:
            json = response[1]
            logging.info(json)
            if str(json).startswith("No player found"):
                await error_embed(ctx, f"Could not find player with name `{username}`")
                return
            if json["uuid"]:
                player_id = json["id"]
            else:
                await error_embed(ctx, f"The following player does not have a UUID in the API `{username}`")
                return
        else:
            await error_embed(ctx, f"Failed to get player ID for name `{username}`")
            return
        discord_message = await ctx.send(content="Grabbing your data")
        stats_response = await request_async_json(stats_from_id_url.format(player_id), 'text/plain')
        json_response = stats_response[1]
        if json_response["data"]:
            data = json_response["data"]
        else:
            logging.info(f"Player data for `{username}` is not loaded yet")
            await discord_message.edit(content="Your data is not loaded yet, hold tight")
            async with aiohttp.ClientSession() as session:
                async with session.get(new_player_request_url.format(player_id)) as r:
                    if r.status == 200:
                        text = await r.text()
                        if text == "Success":
                            logging.info("Successfully loaded new data")
                            await discord_message.edit(content="Your data is being loaded.")
                            await async_sleep(10)
                            stats_response = await request_async_json(stats_from_id_url.format(player_id), 'text/plain')
                            json_response = stats_response[1]
                            data = json_response["data"]
                            if not data:
                                await discord_message.edit(content=f"Account `{username}` doesn't appear to have any"
                                                                   f" data, sorry. Try again later.")
                                return
                            else:
                                await discord_message.edit(content="Data loaded")
                        else:
                            await error_embed(ctx, text)
                            return
                    else:
                        await discord_message.edit(content="Request to load new player data failed")
                        return
        class_stats_list = []
        link = "https://www.nineonefive.xyz/stats/"
        for class_name in data[mode].keys():
            class_stats = data[mode][class_name]
            class_stats_string = f"**{class_name.title()}**\n\n" + "\n"\
                .join([f"**{stat_key.replace('_', ' ').title()}**: `{int(round(float(class_stats[stat_key]), 0))}`"
                       for stat_key in class_stats.keys() if class_stats[stat_key] != "0"]) + "\n"

            # Damage per 20 minutes
            if float(class_stats["damage_dealt"]) > 1000 and float(class_stats["playtime"]) > 1000:
                dmg = float(class_stats["damage_dealt"])
                n_20 = float(class_stats["playtime"]) / 1200
                dmg_per_20 = int(round(dmg / n_20, 0))
                class_stats_string += f"\n**Damage per 20m**: `{dmg_per_20}`"

            # KDR
            if float(class_stats["kills"]) > 0 and float(class_stats["deaths"]) > 0:
                kdr = round(float(class_stats["kills"])/float(class_stats["deaths"]), 3)
                class_stats_string += f"\n**KDR**: `{kdr}`"

            # Cap success
            if float(class_stats["flags_captured"]) > 0 and float(class_stats["flags_stolen"]) > 0:
                cap_eff = round(float(class_stats["flags_captured"]) / float(class_stats["flags_stolen"]) * 100, 2)
                class_stats_string += f"\n**Capture Success**: `{cap_eff}%`"

            class_stats_string += f"\n\n[Stats sourced from 915's brilliant website]({link})"
            class_stats_list.append(class_stats_string)

        await discord_message.edit(content="Plotting a beautiful graph")
        if not len(data[mode].keys()) > 0:
            await discord_message.edit(content=f"{username} has not played {mode}")
            return
        sizes = [int(data[mode][key]["playtime"]) for key in data[mode].keys()]
        avg_size = sum(sizes) / len(sizes)
        labels = [(key.title() if float(data[mode][key]["playtime"]) > avg_size else "") for key in data[mode].keys()]

        ##Sorting lists as tuples
        list_of_tuples = list(zip(labels, sizes))
        sorted_list = sorted(list_of_tuples, key=lambda tup: tup[1])
        unzipped_list = list(zip(*sorted_list))
        new_labels, new_sizes = list(unzipped_list[0]), list(unzipped_list[1])


        data_stream = pie_chart(new_labels, new_sizes, explode=[0.1 if label else 0 for label in labels],
                                title="Playtime by class")
        data_stream.seek(0)
        chart_file = File(data_stream, filename="pie_chart.png")
        await discord_message.edit(content="Done! Sending results...")
        await ctx.send(file=chart_file)
        await create_list_pages(self.bot, ctx, info=class_stats_list, title=f"{mode.title()} stats | {username}",
                                elements_per_page=1, thumbnails=[f"https://cravatar.eu/helmavatar/{username}/128.png"],
                                can_be_reversed=True)
