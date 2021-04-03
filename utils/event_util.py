from calendar import month_name
from datetime import datetime, time, date, timedelta
from re import fullmatch

from discord import Embed, Colour
from pytz import timezone
from utils.config import TIMEZONE

from database.Player import Player, PlayerDoesNotExistError
from database.Signup import Signup
from utils.utils import error_embed
from random import shuffle


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
            signups_tag_str += f"@{user} \n"
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

def get_embed_time_string(time):
    # Get string of event time
    if time.hour >= 13:
        hour = time.hour - 12
        time_suffix = "pm"
    elif time.hour == 12:
        hour = time.hour
        time_suffix = "pm"
    elif time.hour > 0:
        hour = time.hour
        time_suffix = "am"
    else:
        hour = time.hour + 12
        time_suffix = "am"
    if time.minute == 0:
        minute = ""
    elif time.minute < 10:
        minute = f":0{time.minute}"
    else:
        minute = f":{time.minute}"
    if time.date() == time.date():
        date_string = ""
    elif time.year == time.year:
        date_string = f" - {month_name[time.month]} {time.day}"
    else:
        date_string = f" - {month_name[time.month]} {time.day}, {time.year}"
    event_string = f"{hour}{minute}{time_suffix}{date_string}"
    return event_string


def priority_rng_signups(playing_signups_list, size):
    """
    Randomly generates a list of signups. To be used for PUG events.

    If a player is not registered / does not exist, they will not be included in the random list.
    Handle this accordingly - a list of unregistered players is returned by this function.

    :param playing_signups_list: A list of Signup objects
    :param size: The amount of players you would like to include in the output list
    :return: (selected_players, benched_players, unregistered_signups)
    """
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


async def get_event_time(ctx, event_time, event_date, deadline):
    current_datetime = datetime.now(timezone(TIMEZONE))

    # Get time of event
    hour = 0
    minute = 0
    if fullmatch("^((0?[1-9])|(1[0-2]))(:[0-5][0-9])?[ap]m$", event_time):
        is_hour = True
        is_minute = False
        if_m = False
        for c in event_time:
            if is_hour:
                if c == ':':
                    is_minute = True
                    is_hour = False
                elif c == 'a' or c == 'p':
                    if_m = True
                    is_hour = False
                else:
                    hour *= 10
                    hour += int(c)
            elif is_minute:
                if c == 'a' or c == 'p':
                    if_m = True
                    is_minute = False
                else:
                    minute *= 10
                    minute += int(c)
            if if_m:
                if c == 'p' and hour != 12:
                    hour += 12
                    if hour == 24:
                        hour = 0
    elif fullmatch("^(([01]?[0-9])|(2[0-3]))(:[0-5][0-9])?$", event_time):
        is_hour = True
        is_minute = False
        for c in event_time:
            if is_hour:
                if c == ':':
                    is_minute = True
                    is_hour = False
                else:
                    hour *= 10
                    hour += int(c)
            elif is_minute:
                minute *= 10
                minute += int(c)
    else:
        await error_embed(ctx, "Event time is not in a valid format.  Use HH:MMam/pm or HH:MM")
        return False
    event_time = time(hour=hour, minute=minute)

    # Get date of event
    if not event_date:
        event_date = date(current_datetime.year, current_datetime.month, current_datetime.day)
        if event_time.hour < current_datetime.hour:
            event_date += timedelta(days=1)
        elif event_time.hour == current_datetime.hour and event_time.minute <= current_datetime.minute:
            event_date += timedelta(days=1)
    else:
        try:
            event_date = date.fromisoformat(event_date)
        except ValueError:
            await error_embed(ctx, "Event date is not in a valid format.  Use YYYY-MM-DD")
            return False
    event_datetime = timezone(TIMEZONE).localize(datetime.combine(event_date, event_time))

    if event_datetime < current_datetime:
        await error_embed(ctx, "Event time is before the current time.")
        return False

    # Get string of event time
    if event_datetime.hour >= 13:
        hour = event_datetime.hour - 12
        time_suffix = "pm"
    elif event_datetime.hour == 12:
        hour = event_datetime.hour
        time_suffix = "pm"
    elif event_datetime.hour > 0:
        hour = event_datetime.hour
        time_suffix = "am"
    else:
        hour = event_datetime.hour + 12
        time_suffix = "am"
    if event_datetime.minute == 0:
        minute = ""
    elif event_datetime.minute < 10:
        minute = f":0{event_datetime.minute}"
    else:
        minute = f":{event_datetime.minute}"
    if event_datetime.date() == current_datetime.date():
        date_string = ""
    elif event_datetime.year == current_datetime.year:
        date_string = f" - {month_name[event_datetime.month]} {event_datetime.day}"
    else:
        date_string = f" - {month_name[event_datetime.month]} {event_datetime.day}, {event_datetime.year}"
    event_string = f"{hour}{minute}{time_suffix}{date_string}"

    # Get string of signup deadline
    signup_deadline = event_datetime - timedelta(minutes=deadline)
    if signup_deadline <= current_datetime:
        signup_deadline = event_datetime
    if signup_deadline.hour >= 13:
        hour = signup_deadline.hour - 12
        time_suffix = "pm"
    elif signup_deadline.hour == 12:
        hour = signup_deadline.hour
        time_suffix = "pm"
    elif signup_deadline.hour > 0:
        hour = signup_deadline.hour
        time_suffix = "am"
    else:
        hour = signup_deadline.hour + 12
        time_suffix = "am"
    if signup_deadline.minute == 0:
        minute = ""
    elif signup_deadline.minute < 10:
        minute = f":0{signup_deadline.minute}"
    else:
        minute = f":{signup_deadline.minute}"
    if signup_deadline.date() == current_datetime.date():
        date_string = ""
    elif signup_deadline.year == current_datetime.year:
        date_string = f" - {month_name[signup_deadline.month]} {signup_deadline.day}"
    else:
        date_string = f" - {month_name[signup_deadline.month]} {signup_deadline.day}, {signup_deadline.year}"
    deadline_string = f"{hour}{minute}{time_suffix}{date_string}"

    return [(event_datetime, event_string), (signup_deadline, deadline_string)]


def save_signups(db_signups, signups):
    [signup.update_db() for signup in signups]
    [signup.delete() for signup in db_signups if signup not in signups]


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
    embed_description = f"**Time:**\n{event_time}\n\n**Signup Deadline:**\n{signup_deadline}\n\n{description}\n\n" \
                        f"React with ✅ to play\nReact with 🔇 if you cannot speak\nReact with 🛗 if you are able to sub"
    embed = Embed(title=title, description=embed_description, color=Colour.light_grey())
    if mention_role.lower() == "none":
        mention_role = ""
    announcement_message = await announcement_channel.send(content=f"{mention_role}", embed=embed)
    embed.set_footer(text=f"Event ID: {announcement_message.id}")
    await announcement_message.edit(embed=embed)
    description = f"{title}\n\n**Time:**\n{event_time}\n\n**Signup Deadline:**\n{signup_deadline}\n\n{description}"
    embed = Embed(title="Signups", description=description, color=Colour.light_grey())
    embed.add_field(name="✅ Players: 0", value="No one :(", inline=False)
    embed.add_field(name="🛗 Subs: 0", value="No one :(", inline=False)
    signup_list_message = await signup_list_channel.send(embed=embed)

    await announcement_message.add_reaction("✅")
    await announcement_message.add_reaction("🔇")
    await announcement_message.add_reaction("🛗")

    return [announcement_message.id, signup_list_message.id]
