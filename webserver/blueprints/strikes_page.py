from quart import Blueprint, render_template, redirect, url_for, request, jsonify
from bot import bot
from webserver.app import fetch_user_with_perms, discord, fetch_dummy_user
from utils.config import *
from utils.event_util import get_embed_time_string
from datetime import datetime
from database.strikes import *
from discord.utils import get
from logging import info

strikes_blueprint = Blueprint('strikes', __name__)

def get_strike_info_dict(strike, user):
    return {
        "id": strike[0],
        "user": user,
        "issued": get_embed_time_string(datetime.fromisoformat(strike[3])),
        "expiry": get_embed_time_string(datetime.fromisoformat(strike[4])),
        "reason": strike[5]
    }

@strikes_blueprint.route("/strikes")
async def strikes():
    active_strikes = get_all_active_strikes()
    inactive_strikes = get_all_inactive_strikes()

    active_strikes = [
        get_strike_info_dict(
            strike, bot.get_user(strike[1])
        )
        for strike in active_strikes
    ]
    inactive_strikes = [
        get_strike_info_dict(
            strike, bot.get_user(strike[1])
        )
        for strike in inactive_strikes
    ]

    return await render_template(
        "strikes.html",
        active_strikes=active_strikes,
        inactive_strikes=inactive_strikes,
        total_active_strikes=len(active_strikes)
    )