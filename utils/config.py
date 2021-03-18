import json

with open("utils/token.json") as file:
    token_json = json.load(file)

bot_token = token_json["bot_token"]
ELO_FLOOR = 975
MOD_ROLE = "PUG Mod"
ADMIN_ROLE = "PUG Admin"
BOT_OUTPUT_CHANNEL = 816004363544690738
IGN_TRACKER_INTERVAL_HOURS = 12
SIGNUPS_TRACKER_INTERVAL_SECONDS = 10
SLASH_COMMANDS_GUILDS = [753663184228974643]
REGISTER_REQUESTS_CHANNEL = 816389979160313867
FORUM_THREADS_INTERVAL_HOURS = 24
SIGNED_ROLE_NAME = "Signed"

debug = False


def get_debug_status():
    return debug