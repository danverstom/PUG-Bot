from quart import Quart, redirect, url_for, render_template
from quart_discord import DiscordOAuth2Session, requires_authorization, Unauthorized
from json import load
from os import getcwd

with open("utils/app_credentials.json") as file:
    bot_credentials = load(file)

app = Quart(__name__)

app.secret_key = b"asfglokmasgpkloasmgplkasmgplkasmgpmaspgmlpkasgmplkamsg"  # do this better

app.config["DISCORD_CLIENT_ID"] = bot_credentials["oauth2_client_id"]  # Discord client ID.
app.config["DISCORD_CLIENT_SECRET"] = bot_credentials["oauth2_client_secret"]  # Discord client secret.
app.config["DISCORD_REDIRECT_URI"] = bot_credentials["oauth2_callback"]  # URL to your callback endpoint.
app.config["DISCORD_BOT_TOKEN"] = bot_credentials["bot_token"]  # Required to access BOT resources.

# The above items need to be added to utils/app_credentials for this to work

discord = DiscordOAuth2Session(app)


@app.route("/")
@requires_authorization
async def home():
    return await render_template("home.html", user=await discord.fetch_user())



@app.route("/login/")
async def login():
    return await discord.create_session(scope=["identify"])


@app.route("/callback/")
async def callback():
    await discord.callback()
    return redirect(url_for("home"))


@app.errorhandler(Unauthorized)
async def redirect_unauthorized(e):
    return redirect(url_for("login"))


@app.route("/me/")
@requires_authorization
async def me():
    user = await discord.fetch_user()
    return user.to_json()
