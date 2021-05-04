from quart import Blueprint, render_template, redirect, url_for, request, jsonify
from bot import bot
from webserver.app import fetch_user_with_perms, discord, fetch_dummy_user
from utils.config import *
from discord.utils import get
from logging import info

mod_tools_blueprint = Blueprint('moderators', __name__)


@mod_tools_blueprint.route('/moderators/mod_tools')
async def mod_tools():
    if await discord.authorized:
        user = await fetch_user_with_perms()
        if user["is_mod"]:
            guild = bot.get_guild(SLASH_COMMANDS_GUILDS[0])
            text_channels = guild.text_channels
            member = get(guild.members, id=user["user"].id)
            allowed_text_channels = [channel for channel in text_channels if
                                     channel.permissions_for(member).send_messages]
            return await render_template('/moderators/mod_tools.html', user=user,
                                         allowed_text_channels=allowed_text_channels)
        else:
            return redirect(url_for("home"))
    else:
        return redirect(url_for("home"))


@mod_tools_blueprint.route('/moderators/mod_tools/send_message', methods=["POST"])
async def send_message():
    if await discord.authorized:
        user = await fetch_user_with_perms()
        if user["is_mod"]:
            message_info = await request.get_json()
            guild = bot.get_guild(SLASH_COMMANDS_GUILDS[0])

            member = get(guild.members, id=user["user"].id)
            info(message_info)
            info(f"{user['user']} sent message \"{message_info['message']}\"")
            channel = bot.get_channel(int(message_info["channel_id"]))
            allowed_text_channels = [channel for channel in guild.text_channels if
                                     channel.permissions_for(member).send_messages]
            if channel in allowed_text_channels:
                await channel.send(message_info["message"])
            else:
                return jsonify({"success": False, "error": "You do not have perms for this channel"})
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "You need the PUG Mod role to do this"})
    else:
        return jsonify({"success": False, "error": "You are not logged in with your discord account"})

