from calendar import month_name
from datetime import datetime, time, date, timedelta
from re import fullmatch

from discord import Embed, Colour
from pytz import timezone

from utils.utils import error_embed


async def check_if_cancel(ctx, response):
    if response.content.lower() == "cancel":
        embed = Embed(description="❌ Event Creation Cancelled", color=Colour.green())
        await ctx.send(embed=embed)
        return True
    else:
        return False


async def get_event_time(ctx, event_time, event_date, deadline):
    current_datetime = datetime.now(timezone('EST'))

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
                if c == 'p':
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
    event_time = time(hour=hour, minute=minute, tzinfo=timezone('EST'))

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
    event_datetime = datetime.combine(event_date, event_time, timezone('EST'))

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


async def announce_event(title, description, announcement_channel, signup_list_channel, mention_role, event_time,
                         signup_deadline):
    embed_description = f"**Time:**\n{event_time}\n\n**Signup Deadline:**\n{signup_deadline}\n\n{description}\n\n" \
                        f"React with ✅ to play\nReact with ❌ if you can't play\nReact with :mute: if you cannot " \
                        f"speak\nReact with :elevator: if you are able to sub"
    embed = Embed(title=title, description=embed_description, color=Colour.light_grey())
    if mention_role.lower() == "none":
        mention_role = ""
    announcement_message = await announcement_channel.send(content=f"{mention_role}", embed=embed)

    description = f"{title}\n\n**Time:**\n{event_time}\n\n**Signup Deadline:**\n{signup_deadline}\n\n{description}"
    embed = Embed(title="Signups", description=description, color=Colour.light_grey())
    embed.add_field(name="✅ Players: 0", value="No one :(", inline=False)
    embed.add_field(name="🛗 Subs: 0", value="No one :(", inline=False)
    signup_list_message = await signup_list_channel.send(embed=embed)

    await announcement_message.add_reaction("✅")
    await announcement_message.add_reaction("🔇")
    await announcement_message.add_reaction("🛗")

    return [announcement_message.id, signup_list_message.id]
