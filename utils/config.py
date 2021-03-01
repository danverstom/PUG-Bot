import json

with open("utils/token.json") as file:
    token_json = json.load(file)

bot_token = token_json["bot_token"]
ELO_FLOOR = 975
