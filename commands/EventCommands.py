from discord import Embed, Colour
from discord.ext.commands import Cog, has_role
from discord_slash.cog_ext import cog_slash
from discord_slash.utils import manage_commands as mc
from datetime import date, datetime, time, timedelta
from pytz import timezone
from calendar import month_name

from utils.config import SLASH_COMMANDS_GUILDS, MOD_ROLE
from utils.utils import error_embed, response_embed


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
        is_custom_date = False
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
            return False
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

    return f"{event_hour}{event_minute}{hour_suffix} EST, {event_month} {event_datetime.day}, {event_datetime.year}"


class EventCommands(Cog, name="Event Commands"):
    """
    This category contains event commands that can be used by pug mods+
    """

    def __init__(self, bot):
        self.bot = bot

    @cog_slash(name="event", description="Creates an event.",
               options=[mc.create_option(name="title",
                                         description="The title of the event",
                                         option_type=3, required=True),
                        mc.create_option(name="announcement_channel",
                                         description="Channel to announce the event",
                                         option_type=7, required=True),
                        mc.create_option(name="mention_role",
                                         description="Role to mention when event is announced",
                                         option_type=8, required=True),
                        mc.create_option(name="signup_list_channel",
                                         description="Channel to list the signups of the event",
                                         option_type=7, required=True),
                        mc.create_option(name="signup_role",
                                         description="Role to give users that signed up",
                                         option_type=8, required=True),
                        mc.create_option(name="event_time",
                                         description="Time (in EST) of the event.  Must be in 24 hour HH:MM format",
                                         option_type=3, required=True),
                        mc.create_option(name="event_date",
                                         description="Date of the event.  Must be in YYYY-MM-DD format",
                                         option_type=3, required=False)],
               guild_ids=SLASH_COMMANDS_GUILDS)
    @has_role(MOD_ROLE)
    async def event(self, ctx, title, announcement_channel, mention_role, signup_list_channel, signup_role, event_time,
                    event_date=""):
        event_time_str = await get_event_time(ctx, event_time, event_date)
        if not event_time_str:
            return

        def check(m):
            return m.author == ctx.author

        embed = Embed(title="Event Creation", color=Colour.dark_purple())
        embed.add_field(name="Description:", value="Enter the description of the event")
        embed.set_footer(text="Type \"cancel\" to cancel the event")
        message = await ctx.send(embed=embed)
        response = await self.bot.wait_for("message", check=check)
        if await check_if_cancel(ctx, response):
            return
        description = response.content
        await message.delete()
        await response.delete()

        embed_description = f"**Title:** {title}\n**Time:** {event_time_str}\n**Description:**\n{description}\n"
        embed_description = embed_description + f"**Announcement Channel:** {announcement_channel}\n**Mention Role:**"
        embed_description = embed_description + f": {mention_role}\n**Signups List Channel:** {signup_list_channel}\n"
        embed_description = embed_description + f"**Signup Role:** {signup_role}"
        message = await ctx.send(embed=Embed(title="Is everything correct? (y/n):", description=embed_description,
                                   color=Colour.dark_purple()))
        response = await self.bot.wait_for("message", check=check)
        is_correct = response.content.lower() == "y" or response.content.lower() == "yes"
        await message.delete()
        await response.delete()
        if is_correct:
            await response_embed(ctx, "✅ Creating event now")
            # TODO: Do more event stuff
        else:
            await ctx.send(embed=Embed(description="❌ Event Creation Cancelled", color=Colour.green()))
