from quart import Quart, redirect, url_for, render_template, jsonify, request, session
import quart_discord.exceptions
from quart_discord import DiscordOAuth2Session, requires_authorization, Unauthorized
from json import load
from os import getcwd, environ, urandom
from bot import bot, slash
from utils.config import *
from utils.event_util import get_embed_time_string
from datetime import datetime
from database.database import get_sorted_elo, fetch_players_list_discord_id
from database.Event import Event, EventDoesNotExistError
from database.Player import Player
from database.Signup import Signup
from discord import Status
from discord.utils import get
from markdown import markdown
from secrets import token_urlsafe
from logging import info

with open("utils/app_credentials.json") as file:
    bot_credentials = load(file)

app = Quart(__name__)

app.secret_key = token_urlsafe(24)

app.config["DISCORD_CLIENT_ID"] = bot_credentials["oauth2_client_id"]  # Discord client ID.
app.config["DISCORD_CLIENT_SECRET"] = bot_credentials["oauth2_client_secret"]  # Discord client secret.
app.config["DISCORD_REDIRECT_URI"] = bot_credentials["oauth2_callback"]  # URL to your callback endpoint.
app.config["DISCORD_BOT_TOKEN"] = bot_credentials["bot_token"]  # Required to access BOT resources.
environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# The above items need to be added to utils/app_credentials for this to work

discord = DiscordOAuth2Session(app)


async def fetch_dummy_user():
    """for dev purposes"""
    user = bot.get_user(175964671520669696)
    guild = bot.get_guild(SLASH_COMMANDS_GUILDS[0])
    admin_role = get(guild.roles, name=ADMIN_ROLE)
    mod_role = get(guild.roles, name=MOD_ROLE)
    member = get(guild.members, id=user.id)
    if member:
        return {"user": user,
                "is_admin": member.top_role.position >= admin_role.position,
                "is_mod": member.top_role.position >= mod_role.position,
                "in_server": True}
    else:
        return {"user": user,
                "is_admin": False,
                "is_mod": False,
                "in_server": False}


async def fetch_user_with_perms():
    user = await discord.fetch_user()
    guild = bot.get_guild(SLASH_COMMANDS_GUILDS[0])
    admin_role = get(guild.roles, name=ADMIN_ROLE)
    mod_role = get(guild.roles, name=MOD_ROLE)
    member = get(guild.members, id=user.id)
    if member:
        return {"user": user,
                "is_admin": member.top_role.position >= admin_role.position,
                "is_mod": member.top_role.position >= mod_role.position,
                "in_server": True}
    else:
        return {"user": user,
                "is_admin": False,
                "is_mod": False,
                "in_server": False}


@app.before_request
def make_session_permanent():
    session.permanent = True



@app.route("/")
async def home():
    if await discord.authorized:
        user = await fetch_user_with_perms()
    else:
        user = False
    guilds = ', '.join([bot.get_guild(guild_id).name for guild_id in SLASH_COMMANDS_GUILDS])
    registered_users = len(fetch_players_list_discord_id())
    online_members = sum(member.status != Status.offline and not member.bot for member in
                         bot.get_guild(SLASH_COMMANDS_GUILDS[0]).members)
    return await render_template("home.html", discord_invite=PUG_INVITE_LINK, guilds=guilds,
                                 registered_users=registered_users, online_members=online_members, user=user)


@app.route("/leaderboard")
async def leaderboard():
    player = None
    if await discord.authorized:
        user = await fetch_user_with_perms()
        player = Player.exists_discord_id(user["user"].id)
    else:
        user = False
    if player:
        player.leaderboard_position = False
    data = get_sorted_elo()
    position = 1
    for item in data:
        data[position - 1] = (item[0], item[1], item[2], position)
        if player:
            if item[0] == player.minecraft_username:
                player.leaderboard_position = position
        position += 1
    return await render_template("leaderboard.html", data=data, user=user, player=player)


@app.route("/events")
async def events():
    if await discord.authorized:
        user = await fetch_user_with_perms()
    else:
        user = False
    all_events = Event.fetch_events_list()
    for event_obj in all_events:
        event_obj.time_est = get_embed_time_string(datetime.fromisoformat(event_obj.time_est))
        event_obj.signup_deadline = get_embed_time_string(datetime.fromisoformat(event_obj.signup_deadline))
    active_events = [event for event in all_events if event.is_active]
    inactive_events = [event for event in all_events if not event.is_active]
    return await render_template("events.html", active_events=active_events, inactive_events=inactive_events,
                                 total_active_events=len(active_events), user=user)


@app.route("/help")
async def help_page():
    if await discord.authorized:
        user = await fetch_user_with_perms()
    else:
        user = False
    commands = slash.commands
    info = ""
    help_list = []
    for command in commands:
        options = commands[command].options
        guilds = ', '.join([bot.get_guild(guild_id).name for guild_id in commands[command].allowed_guild_ids])
        command_help = {
            "options": options,
            "guilds": guilds,
            "description": markdown(commands[command].description) if commands[command].description
            else "No Description",
            "command_name": command
        }
        help_list.append(command_help)
    return await render_template("help.html", help_list=help_list, user=user)


@app.route("/event/<event_id>")
async def event(event_id: int):
    try:
        event_from_id = Event.from_event_id(event_id)
    except EventDoesNotExistError:
        return await render_template("page_not_found.html"), 404
    else:
        signups = Signup.fetch_signups_list(event_id)
        for signup in signups:
            signup.user = bot.get_user(signup.user_id)
            signup.player = Player.exists_discord_id(signup.user_id)
        event_from_id.time_est = get_embed_time_string(datetime.fromisoformat(event_from_id.time_est))
        event_from_id.signup_deadline = get_embed_time_string(datetime.fromisoformat(event_from_id.signup_deadline))
        event_from_id.description = markdown(event_from_id.description)\
            if event_from_id.description else "No Description"
        return await render_template("event.html", event=event_from_id, signups=signups)


@app.route("/login/")
async def login():
    return await discord.create_session(scope=["identify"])


@app.route("/logout/")
async def logout():
    user = await discord.fetch_user()
    info(f"{user} just logged out")
    discord.revoke()
    return redirect(url_for("home"))


@app.route("/callback/")
async def callback():
    try:
        await discord.callback()
    except quart_discord.exceptions.AccessDenied:
        return redirect(url_for("home"))
    finally:
        user = await discord.fetch_user()
        info(f"{user} just logged in")
    return redirect(url_for("home"))


@app.errorhandler(Unauthorized)
async def redirect_unauthorized(e):
    return redirect(url_for("login"))


@app.errorhandler(404)
async def page_not_found(e):
    return await render_template("page_not_found.html"), 404


@app.route("/me/")
@requires_authorization
async def me():
    user = await discord.fetch_user()
    return user.to_json()

from webserver.blueprints.mod_tools import mod_tools_blueprint
from webserver.blueprints.strikes_page import strikes_blueprint

app.register_blueprint(mod_tools_blueprint)
app.register_blueprint(strikes_blueprint)
