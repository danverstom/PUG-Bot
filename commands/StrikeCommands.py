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

# TODO: Create task loop which checks + updates strikes
#       this should set is_active=False (needs another DB method) after the expiry period and then
#       delete the record from the db entirely after a period of days defined in config.py

# TODO: Add Player.is_striked() method
# TODO: block striked players from signing up to events
# TODO: Allocate + maintain "Striked" role to striked players (task loop)

def calculate_new_strike_duration(user_id):
    default_strike_days = 1
    total_strikes = len(get_all_strikes(user_id))
    if not total_strikes:
        return default_strike_days
    else:
        return default_strike_days + default_strike_days * (total_strikes**2)


class StrikeCommands(Cog, name="Strike Commands"):
    def __init__(self, bot):
        self.bot = bot

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
        duration_days = calculate_new_strike_duration(user.id)
        time_now = datetime.now(timezone(TIMEZONE))
        expiry_date = time_now + timedelta(days=duration_days)
        total_strikes = len(get_all_strikes(user.id))
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
                f"Since you were striked {total_strikes} time{'s' if total_strikes else ''} before, this strike will last {duration_days} days.\n"
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
    async def strike_view(self, ctx, user = False):
        if not user:
            user = ctx.author
        active_strikes = get_active_strikes(user.id)
        inactive_strikes = get_inactive_strikes(user.id)
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
        print(member)
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