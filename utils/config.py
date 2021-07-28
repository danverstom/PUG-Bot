import json
import logging

with open("utils/app_credentials.json") as file:
    token_json = json.load(file)

bot_token = token_json["bot_token"]
ELO_FLOOR = 975
MOD_ROLE = "PUG Mod"
ADMIN_ROLE = "PUG Dev"
PROSPECT_ROLE = "Prospect"
BOT_OUTPUT_CHANNEL = 816004363544690738
PUBLIC_BOT_CHANNEL = 816004363544690738
IGN_TRACKER_INTERVAL_HOURS = 12
SIGNUPS_TRACKER_INTERVAL_SECONDS = 10
SLASH_COMMANDS_GUILDS = [753663184228974643]
REGISTER_REQUESTS_CHANNEL = 816389979160313867
FORUM_THREADS_INTERVAL_HOURS = 6
SIGNED_ROLE_NAME = "Signed"
SPECTATOR_ROLE_NAME = "Spectator"
GENERAL_CHAT = 753663185093132309
TIMEZONE = "US/Eastern"
PUG_INVITE_LINK = "https://discord.gg/Gqpv5yUhAd"
TEAMS_ROLES = ["Team 1 [Red]", "Team 2 [Blue]"]
PPM_ROLES = ["Red Team", "Blue Team", "Green Team", "Yellow Team", "Signed", "Spectator"]
STRIKE_REASONS = [
    "Late",
    "No Show",
    "Left the game without agreeing with host",
    "Trolling",
    "Throwing",
    "Harassment",
    "AFK",
    "Not joining team call",
    "Evading a strike",
    "Unsigning too late",
    "Other"
]


SYNC_COMMANDS = True
BOT_START_MESSAGE = True
UPDATE_NICKNAMES = True
PRIORITY_DEFAULT = True
SIGNUP_DEADLINE_DEFAULT = 30
SEND_JOIN_MESSAGE = True

WEB_SERVER_HOSTNAME = "localhost"
WEB_SERVER_PORT = 8080
WEB_URL = "http://localhost:8080"

BOT_OWNER_ID = 175964671520669696


debug = False


def get_debug_status():
    return debug


logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.INFO) #local time !
