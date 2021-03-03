from calendar import month_name
from datetime import datetime, time, date, timedelta

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


async def get_event_time(ctx, event_time, event_date):
    current_date = datetime.now(timezone('EST'))
    try:
        event_time = time.fromisoformat(event_time)
    except ValueError:
        await error_embed(ctx, "Incorrect time format.  Use the 24 hour HH:MM format (09:00, 20:30)")
        return False
    if not event_date:
        event_date = date(current_date.year, current_date.month, current_date.day)
        is_custom_date = []
    else:
        try:
            event_date = date.fromisoformat(event_date)
        except ValueError:
            await error_embed(ctx, "Incorrect date format.  Use the YYYY-MM-DD format (2021-01-21)")
            return False
        is_custom_date = True

    event_datetime = datetime.combine(event_date, event_time, timezone('EST'))

    if event_datetime <= current_date:
        if is_custom_date:
            await error_embed(ctx, "Event time is before current time.")
            return []
        else:
            event_datetime = event_datetime + timedelta(days=1)

    if event_datetime.minute == 0:
        event_minute = ""
    elif event_datetime.minute < 10:
        event_minute = f":0{event_datetime.minute}"
    else:
        event_minute = f":{event_datetime.minute}"

    if event_datetime.hour == 0:
        event_hour = 12
        hour_suffix = "pm"
    elif event_datetime.hour < 12:
        event_hour = event_datetime.hour
        hour_suffix = "am"
    elif event_datetime.hour == 12:
        event_hour = event_datetime.hour
        hour_suffix = "pm"
    else:
        event_hour = event_datetime.hour - 12
        hour_suffix = "pm"

    event_month = month_name[event_datetime.month]

    return [event_datetime,
            f"{event_hour}{event_minute}{hour_suffix} EST, {event_month} {event_datetime.day}, {event_datetime.year}"]
