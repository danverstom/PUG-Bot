from utils.database import fetch_player_id, fetch_discord_id, fetch_minecraft_username


class Player:
    minecraft_id = ""
    discord_id = ""
    minecraft_username = ""
    elo = 0
    priority = 0

    def __init__(self, minecraft_id="", discord_id=0, minecraft_username=""):
        pass
