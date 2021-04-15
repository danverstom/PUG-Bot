from quart import Quart, redirect, url_for, render_template, jsonify, request
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
from markdown import markdown
from secrets import token_urlsafe

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


@app.route("/")
async def home():
    guilds = ', '.join([bot.get_guild(guild_id).name for guild_id in SLASH_COMMANDS_GUILDS])
    registered_users = len(fetch_players_list_discord_id())
    online_members = sum(member.status != Status.offline and not member.bot for member in
                         bot.get_guild(SLASH_COMMANDS_GUILDS[0]).members)
    return await render_template("home.html", discord_invite=PUG_INVITE_LINK, guilds=guilds,
                                 registered_users=registered_users, online_members=online_members)


@app.route("/leaderboard")
@requires_authorization
async def leaderboard():
    user_details = await discord.fetch_user()
    player = Player.exists_discord_id(user_details.id)
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
    return await render_template("leaderboard.html", data=data, user=user_details, player=player)


@app.route("/events")
async def events():
    all_events = Event.fetch_events_list()
    for event_obj in all_events:
        event_obj.time_est = get_embed_time_string(datetime.fromisoformat(event_obj.time_est))
        event_obj.signup_deadline = get_embed_time_string(datetime.fromisoformat(event_obj.signup_deadline))
    active_events = [event for event in all_events if event.is_active]
    inactive_events = [event for event in all_events if not event.is_active]
    return await render_template("events.html", active_events=active_events, inactive_events=inactive_events,
                                 total_active_events=len(active_events))


@app.route("/help")
async def help_page():
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
    return await render_template("help.html", help_list=help_list)


@app.route("/event/<event_id>")
@requires_authorization
async def event(event_id: int):
    user_details = await discord.fetch_user()
    try:
        event_from_id = Event.from_event_id(event_id)
        player = Player.exists_discord_id(user_details.id)
        signed = False
        if player:
            signups = Signup.fetch_signups_list(event_id)
            if player.discord_id in [signup.user_id for signup in signups]:
                signed = True
    except EventDoesNotExistError:
        return await render_template("page_not_found.html"), 404
    else:
        event_from_id.time_est = get_embed_time_string(datetime.fromisoformat(event_from_id.time_est))
        event_from_id.signup_deadline = get_embed_time_string(datetime.fromisoformat(event_from_id.signup_deadline))
        event_from_id.description = markdown(event_from_id.description)\
            if event_from_id.description else "No Description"
        return await render_template("event.html", event=event_from_id, signed=signed)


@app.route("/login/")
async def login():
    return await discord.create_session(scope=["identify"])


@app.route("/callback/")
async def callback():
    try:
        await discord.callback()
    except quart_discord.exceptions.AccessDenied:
        redirect(url_for("home"))
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
