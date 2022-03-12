from calendar import month_name
from datetime import datetime, time, date, timedelta
from re import fullmatch

from discord import Embed, Colour
from pytz import timezone
from utils.config import TIMEZONE, WEB_URL
import os


from database.Player import Player, PlayerDoesNotExistError
from database.Signup import Signup
from utils.utils import error_embed
from random import shuffle, seed
from dateutil import parser
from logging import info



def generate_signups_embed(bot, signups, event):
    embed = Embed(title=f"Signups - {event.title}", colour=Colour.dark_purple())
    playing_signups = []
    sub_signups = []
    unregistered_signups = [signup for signup in signups if not Player.exists_discord_id(signup.user_id)]
    for signup in signups:
        if signup.can_play:
            playing_signups.append(signup)
        if signup.can_sub:
            sub_signups.append(signup)
    signups_tag_str = ""
    subs_tag_str = ""
    if len(playing_signups) > 0:
        for signup in playing_signups:
            user = bot.get_user(signup.user_id)
            player = Player.exists_discord_id(signup.user_id)
            signups_tag_str += f"@{user} ({player.minecraft_username if player else 'Unregistered'})\n"
    else:
        signups_tag_str = "Nobody :("
    if len(sub_signups) > 0:
        for signup in sub_signups:
            user = bot.get_user(signup.user_id)
            subs_tag_str += f"@{user} \n"
    else:
        subs_tag_str = "Nobody :("
    embed.add_field(name="Signed", value=f"```{signups_tag_str}```", inline=False)
    embed.add_field(name="Can Sub", value=f"```{subs_tag_str}```", inline=False)
    if unregistered_signups:
        tags = "\n".join([f"@{bot.get_user(signup.user_id)} " for signup in unregistered_signups])
        embed.add_field(name="Unregistered:", value=f"```{tags}```", inline=False)
    return embed

def get_embed_time_string(datetime):
    # Get string of event time
    current_datetime = datetime.now(timezone(TIMEZONE))
    r = "-"
    if os.name == "nt":
        r = "#" # TODO better ways of removing padding?
    string = datetime.strftime(f"%{r}I:%M%p")

    if datetime.date() == current_datetime.date(): # if dd-mm-yyyy is the same
        pass
    elif current_datetime.year == datetime.year: # both in the same year
        string += " " + datetime.strftime(f"%B %{r}d")
    else: 
        string += " " + datetime.strftime(f"%B %{r}d %Y")
    return string

async def get_event_time(ctx, time_string, date_string, deadline):
    current_datetime = datetime.now(timezone(TIMEZONE))
    # Get time of event
    event_time = None
    try:
        event_time = parser.parse(time_string)
    except Exception as e:
        await error_embed(ctx, "Event time is not in a valid format.  Use HH:MMam/pm or HH:MM")
        return False

    # Get date of event
    event_date = None
    if not date_string:
        event_date = date(current_datetime.year, current_datetime.month, current_datetime.day)
        if (event_time.hour < current_datetime.hour) or (event_time.hour == current_datetime.hour and event_time.minute <= current_datetime.minute):
            event_date += timedelta(days=1)
    else:
        try:
            event_date = parser.parse(date_string, dayfirst=True) # could remove dayfirst for MM-DD-YYYY for the americans
        except Exception as e:
            await error_embed(ctx, "Event date is not in a valid format. Use DD-MM-YYYY")
            return False
        
    event_datetime = datetime.combine(event_date, event_time.time())
    event_datetime = timezone(TIMEZONE).localize(event_datetime) # turn into offset-aware datetime object

    if event_datetime < current_datetime:
        await error_embed(ctx, "Event time is before the current time.")
        return False

    r = "-"
    if os.name == "nt":
        r = "#" # TODO better ways of removing padding?
        
    # Get string of event time
    event_string = event_datetime.strftime(f"%{r}I:%M%p") 
    if date_string:
        if current_datetime.year == event_datetime.year:
            event_string += " " + event_date.strftime(f"%B %{r}d")
        else:
            event_string += " " + event_date.strftime(f"%B %{r}d %Y")

    # Get string of signup deadline
    signup_deadline = event_datetime - timedelta(minutes=deadline)
    if signup_deadline <= current_datetime:
        signup_deadline = event_datetime
    
    deadline_string = signup_deadline.strftime(f"%{r}I:%M%p")
    if date_string:
        if current_datetime.year == event_datetime.year:
            deadline_string += " " + event_date.strftime(f"%B %{r}d")
        else:
            deadline_string += " " + event_date.strftime(f"%B %{r}d %Y")
    return [(event_datetime, event_string), (signup_deadline, deadline_string)]


def priority_rng_signups(playing_signups_list, size):
    """
    Randomly generates a list of signups. To be used for PUG events.

    If a player is not registered / does not exist, they will not be included in the random list.
    Handle this accordingly - a list of unregistered players is returned by this function.

    :param playing_signups_list: A list of Signup objects
    :param size: The amount of players you would like to include in the output list
    :return: (selected_players, benched_players, unregistered_signups)
    """
    seed()
    players = []
    unregistered_signups = []
    for signup in playing_signups_list:
        try:
            players.append(Player.from_discord_id(signup.user_id))
        except PlayerDoesNotExistError:
            unregistered_signups.append(signup)
    shuffle(players)
    players = sorted(players, key=lambda item: item.priority, reverse=True)
    selected_players = players[:size]
    for player in selected_players:
        player.set_priority(0)
    benched_players = players[size:]
    for player in benched_players:
        player.change_priority(1)
    return selected_players, benched_players, unregistered_signups


async def check_if_cancel(ctx, response):
    if response.content.lower() == "cancel":
        embed = Embed(description="❌ Event Creation Cancelled", color=Colour.green())
        await ctx.send(embed=embed)
        return True
    else:
        return False


def save_signups(db_signups, signups):
    [signup.update_db() for signup in signups]
    # [signup.delete() for signup in db_signups if signup not in signups]
    for signup in db_signups:
        if signup not in signups:
            signup.delete()
            info(f"Deleting signup {signup.user_id} from event {signup.event_id}")


def reaction_changes(signups, can_play, is_muted, can_sub, event_id):
    old_can_play = [user.user_id for user in signups if user.can_play]
    old_is_muted = [user.user_id for user in signups if user.is_muted]
    old_can_sub = [user.user_id for user in signups if user.can_sub]

    diff = set(old_can_play) != set(can_play) or set(old_is_muted) != set(is_muted) or set(old_can_sub) != set(can_sub)

    stl_can_play = [user for user in old_can_play if user in can_play]
    add_can_play = [user for user in can_play if user not in old_can_play]
    only_can_sub = [user for user in can_sub if user not in can_play]

    all_signups = dict()
    for user in can_play:
        all_signups[user] = Signup.create_signup(user, event_id, True, user in is_muted, user in can_sub)
    for user in only_can_sub:
        all_signups[user] = Signup.create_signup(user, event_id, False, user in is_muted, True)

    new_signups = [all_signups[user] for user in stl_can_play]
    new_signups.extend([all_signups[user] for user in add_can_play])
    new_signups.extend([all_signups[user] for user in only_can_sub])
    return new_signups, diff


async def announce_event(title, description, announcement_channel, signup_list_channel, mention_role, event_time,
                         signup_deadline):
    embed_description = f"**Time:**\n{event_time[0][1]} (<t:{int(event_time[0][0].timestamp())}:R>)\n\n**Signup Deadline:**\n{signup_deadline}\n\n{description}\n\n" \
                        f"React with ✅ to play\nReact with 🔇 if you cannot speak\nReact with 🛗 if you are able to sub"
    embed = Embed(title=title, description=embed_description, color=Colour.dark_purple())
    if mention_role.lower() == "none":
        mention_role = ""
    announcement_message = await announcement_channel.send(content=f"{mention_role}", embed=embed)
    embed.set_footer(text=f"Event ID: {announcement_message.id}")
    embed.description += f"\n[View the event online]({WEB_URL}/event/{announcement_message.id})"
    await announcement_message.edit(embed=embed)
    description = f"{title}\n\n**Time:**\n{event_time[0][1]}  (<t:{int(event_time[0][0].timestamp())}:R>)\n\n**Signup Deadline:**\n{signup_deadline}\n\n{description}"
    embed = Embed(title="Signups", description=description, color=Colour.dark_purple())
    embed.add_field(name="✅ Players: 0", value="No one :(", inline=False)
    embed.add_field(name="🛗 Subs: 0", value="No one :(", inline=False)
    signup_list_message = await signup_list_channel.send(embed=embed)

    await announcement_message.add_reaction("✅")
    await announcement_message.add_reaction("🔇")
    await announcement_message.add_reaction("🛗")
    await announcement_message.add_reaction("🗺️")  # For Mods to react to set up maps

    return [announcement_message.id, signup_list_message.id]
