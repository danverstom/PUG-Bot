from discord import Embed, Colour, User
from discord.ext.commands import Cog
from discord_slash.cog_ext import cog_slash
from discord_slash.utils import manage_commands as mc
from discord.utils import get
from utils.config import *
from utils.utils import *
from utils.event_util import get_embed_time_string
from database.strikes import *
from datetime import timedelta, datetime
from pytz import timezone
from discord.errors import Forbidden
from discord.ext import tasks

# TODO: Make commands / command names more intuitive
# TODO: Make view strikes embed use fields


def calculate_new_strike_duration(user_id):
    default_strike_days = 1
    total_strikes = len(get_all_user_strikes(user_id))
    if not total_strikes:
        return default_strike_days
    else:
        return default_strike_days + default_strike_days * (total_strikes**2)


def get_strike_info_string(strike, user):
    return (
        f"ID: `{strike[0]}`\n"
        f"User: {user.mention if user else strike[1]}\n"  # Replace with user ID if they aren't in the server
        f"Issued: `{get_embed_time_string(datetime.fromisoformat(strike[3]))}`\n"
        f"Expiry: `{get_embed_time_string(datetime.fromisoformat(strike[4]))}`\n"
        f"Reason: {strike[5]}\n"
    )


class StrikeCommands(Cog, name="Strike Commands"):
    def __init__(self, bot):
        self.bot = bot   

    @Cog.listener()
    async def on_ready(self):
        self.bot_channel = self.bot.get_channel(BOT_OUTPUT_CHANNEL)
        self.update_strikes.start()

    def cog_unload(self):
        self.update_usernames.cancel()

    @cog_slash(name="strike",
               description="Strike a player",
               options=[
                    mc.create_option(
                        name="user",
                        description="The user to be striked",
                        option_type=6, required=True
                    ),
                   mc.create_option(
                        name="reason",
                        description="The reason why the user is striked",
                        option_type=3,
                        required=True,
                        choices=[
                            mc.create_choice(value=reason, name=reason) for reason in STRIKE_REASONS
                        ]
                    ),
               ], guild_ids=SLASH_COMMANDS_GUILDS)
    async def strike(self, ctx, user: User, reason: str):
        if not has_permissions(ctx, MOD_ROLE):
            await ctx.send("You do not have sufficient permissions to perform this command", hidden=True)
            return False
        duration_days = calculate_new_strike_duration(user.id)
        time_now = datetime.now(timezone(TIMEZONE))
        expiry_date = time_now + timedelta(days=duration_days)
        total_strikes = len(get_all_user_strikes(user.id))
        add_strike(
            user_id=user.id,
            striked_by=ctx.author.id,
            striked_at=time_now.isoformat(),
            expiry_date=expiry_date.isoformat(),
            strike_reason=reason
        )
        try:
            await response_embed(
                user,
                f"You were striked in {ctx.guild.name}",
                f"Since you were striked {total_strikes} time{'s' if total_strikes != 1 else ''} before, this strike will last {duration_days} days.\n"
                f"Reason: `{reason}`"
            )
        except Forbidden:
            # This means the bot can't DM the user
            await ctx.send("This user has PMs off, failed to send DM.")
        await success_embed(
            ctx,
            f"Striked {user.mention} for {duration_days} days with reason `{reason}`\n"
        )

    @cog_slash(description="View the strikes of yourself or someone else",
               options=[
                   mc.create_option(
                       name="user",
                       description="Some other user",
                       option_type=6, required=False
                   )
               ], guild_ids=SLASH_COMMANDS_GUILDS)
    async def strike_view(self, ctx, user=False):
        if not user:
            user = ctx.author
        active_strikes = get_active_user_strikes(user.id)
        inactive_strikes = get_inactive_user_strikes(user.id)
        content = ""
        if not active_strikes and not inactive_strikes:
            content = f"{user.mention} has no strikes."
        if active_strikes:
            content += "\n**Active Strikes**\n" + "\n".join(
                [
                    f"ID: {strike[0]}\n"
                    f"Issued: `{get_embed_time_string(datetime.fromisoformat(strike[3]))}`\n"
                    f"Expiry: `{get_embed_time_string(datetime.fromisoformat(strike[4]))}`\n"
                    f"Reason: {strike[5]}\n"
                    for strike in active_strikes
                ]
            )
        if inactive_strikes:
            content += "\n**Inactive Strikes**\n" + "\n".join(
                [
                    f"ID: `{strike[0]}`\n"
                    f"Issued: `{get_embed_time_string(datetime.fromisoformat(strike[3]))}`\n"
                    f"Expiry: `{get_embed_time_string(datetime.fromisoformat(strike[4]))}`\n"
                    f"Reason: {strike[5]}\n"
                    for strike in inactive_strikes
                ]
            )
        await response_embed(
            ctx,
            f"Strikes - {user.name}",
            content
        )

    @cog_slash(description="Remove a strike from a player",
               options=[
                   mc.create_option(
                       name="strike_id",
                       description="The strike ID to remove",
                       option_type=4, required=True
                   )
               ], guild_ids=SLASH_COMMANDS_GUILDS)
    async def strike_remove(self, ctx, strike_id: int):
        if not has_permissions(ctx, MOD_ROLE):
            await ctx.send("You do not have sufficient permissions to perform this command", hidden=True)
            return False
        strike = get_strike(strike_id)
        if not strike:
            await error_embed(ctx, "Could not find a strike associated with this ID. Try again.")
            return
        member = ctx.guild.get_member(strike[1])
        member_mention = member.mention if member else "`Not In Server`"
        await response_embed(
            ctx,
            "Confirm Strike Deletion (y/n)",
            f"Member: {member_mention}\n"
            f"ID: `{strike[0]}`\n"
            f"Issued: `{get_embed_time_string(datetime.fromisoformat(strike[3]))}`\n"
            f"Expiry: `{get_embed_time_string(datetime.fromisoformat(strike[4]))}`\n"
            f"Reason: {strike[5]}\n"
        )

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        response = await self.bot.wait_for('message', check=check)
        if response.content.lower() not in ["yes", "y", "confirm", "go", "continue"]:
            await response_embed(ctx, "Cancelled", "Strike deletion was cancelled")
            return

        remove_strike(strike_id)
        await success_embed(ctx, "Removed strike")

    @tasks.loop(minutes=1)
    async def update_strikes(self):
        time_now = datetime.now(timezone(TIMEZONE))
        all_strikes = get_all_strikes()
        for strike in all_strikes:
            strike_expiry_date = datetime.fromisoformat(strike[4])
            strike_date = datetime.fromisoformat(strike[3])
            # If the strike is active and due to expire
            if strike[6] and strike_expiry_date <= time_now:
                change_active_status(strike[0], False)
                user = self.bot.get_user(strike[1])
                await response_embed(
                    self.bot_channel,
                    "Strike Expired",
                    get_strike_info_string(strike, user)
                )
                try:
                    if not user:
                        continue
                    await response_embed(
                        user,
                        "Strike no longer active",
                        get_strike_info_string(strike, user) +
                        "_if you have other strikes active, you may not be able to sign up for events_"
                    )
                except Forbidden:
                    logging.info(
                        f"Could not send DM to {user.mention if user else strike[1]} about their strike")
            # Strikes get deleted 30 days after expiry date
            elif strike_expiry_date + timedelta(days=30) <= time_now:
                remove_strike(strike[0])
                user = self.bot.get_user(strike[1])
                await response_embed(
                    self.bot_channel,
                    "Strike Deleted",
                    get_strike_info_string(strike, user) +
                    f"_this strike will no longer count towards the length of {user.mention if user else strike[1]}'s "
                    f"new strikes_"
                )
                try:
                    if not user:
                        continue
                    await response_embed(
                        user,
                        "Strike deleted from your record",
                        get_strike_info_string(strike, user) +
                        "_this strike will no longer count towards the length of new strikes_"
                    )
                except Forbidden:
                    logging.info(
                        f"Could not send DM to {user.mention if user else strike[1]} about their strike")
