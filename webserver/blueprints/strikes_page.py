from quart import Blueprint, render_template, redirect, url_for, request, jsonify, flash
from bot import bot
from webserver.app import fetch_user_with_perms, discord, fetch_dummy_user
from utils.config import *
from utils.event_util import get_embed_time_string
from utils.utils import *
from datetime import datetime
from database.strikes import *
from discord.utils import get
from discord.errors import Forbidden
from logging import info

strikes_blueprint = Blueprint('strikes', __name__)

def get_strike_info_dict(strike):
    return {
        "id": strike[0],
        "user": bot.get_user(strike[1]),
        "issued": get_embed_time_string(datetime.fromisoformat(strike[3])),
        "expiry": get_embed_time_string(datetime.fromisoformat(strike[4])),
        "reason": strike[5],
        "striked_by": bot.get_user(strike[2])
    }

def get_strike_info_string(strike):
    return (
        f"ID: `{strike[0]}`\n"
        f"User: {bot.get_user(strike[1]).mention}\n"
        f"Issued: `{get_embed_time_string(datetime.fromisoformat(strike[3]))}`\n"
        f"Expiry: `{get_embed_time_string(datetime.fromisoformat(strike[4]))}`\n"
        f"Reason: {strike[5]}\n"
    )

@strikes_blueprint.route("/strikes")
async def strikes():
    if await discord.authorized:
        user = await fetch_user_with_perms()
    else:
        user = False
    active_strikes = get_all_active_strikes()
    inactive_strikes = get_all_inactive_strikes()

    active_strikes = [
        get_strike_info_dict(strike)
        for strike in active_strikes
    ]
    inactive_strikes = [
        get_strike_info_dict(strike)
        for strike in inactive_strikes
    ]

    return await render_template(
        "strikes.html",
        active_strikes=active_strikes,
        inactive_strikes=inactive_strikes,
        total_active_strikes=len(active_strikes),
        user=user
    )

@strikes_blueprint.route("/strikes/remove_strike")
async def remove_strike_endpoint():
    user = await fetch_user_with_perms()
    if user["is_mod"]:
        bot_channel = bot.get_channel(BOT_OUTPUT_CHANNEL)
        strike_id = request.args.get("strike_id")
        strike = get_strike(strike_id)
        if not strike:
            await flash(f"Strike ID {strike_id} does not exist")
            return redirect(url_for("strikes.strikes"))
        remove_strike(strike_id)
        await flash(f"Strike ID {strike_id} removed")
        striked_user = bot.get_user(strike[1])
        await response_embed(
            bot_channel,
            f"Strike removed by {user['user'].name} via Web Dashboard",
            get_strike_info_string(strike)
        )
        striked_user = bot.get_user(strike[1])
        try:
            await response_embed(
                striked_user,
                "Strike deleted (removed by a host)",
                get_strike_info_string(strike) +
                "This strike has been completely removed from your record and won't count towards future punishments"
            )
        except Forbidden:
            info(f"Could not send DM to {striked_user.name} about their strike expiring")
        return redirect(url_for("strikes.strikes"))
    else:
        return redirect(url_for("strikes.strikes"))


@strikes_blueprint.route("/strikes/set_strike_inactive")
async def set_strike_inactive():
    user = await fetch_user_with_perms()
    if user["is_mod"]:
        bot_channel = bot.get_channel(BOT_OUTPUT_CHANNEL)
        strike_id = request.args.get("strike_id")
        strike = get_strike(strike_id)
        if not strike:
            await flash(f"Strike ID {strike_id} does not exist")
            return redirect(url_for("strikes.strikes"))
        change_active_status(strike_id, 0)
        await flash(f"Strike ID {strike_id} set to inactive")
        await response_embed(
            bot_channel,
            f"Strike set to Inactive by {user['user'].name} via Web Dashboard",
            get_strike_info_string(strike)
        )
        striked_user = bot.get_user(strike[1])
        try:
            await response_embed(
                striked_user,
                "Strike no longer active (edited by a host)",
                get_strike_info_string(strike) +
                "_if you have other strikes active, you may not be able to sign up for events_"
            )
        except Forbidden:
            info(f"Could not send DM to {striked_user.name} about their strike expiring")
        return redirect(url_for("strikes.strikes"))
    else:
        return redirect(url_for("strikes.strikes"))