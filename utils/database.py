import sqlite3 as sql
from mojang.api import MojangAPI
from utils.config import ELO_FLOOR

conn = sql.connect("utils/database.db")

conn.execute('''create table if not exists players
                (minecraft_id text, discord_id integer, minecraft_username text, priority integer, elo integer)''')

conn.commit()
c = conn.cursor()


def add_player(minecraft_id, discord_id, minecraft_username, priority=0, elo=1000):
    if fetch_player_id(minecraft_id):
        return 1
    elif fetch_discord_id(discord_id):
        return 2
    c.execute("INSERT INTO players VALUES (?,?,?,?,?)", (minecraft_id, discord_id, minecraft_username, priority, elo))
    conn.commit()
    return 0


def fetch_player_id(minecraft_id):
    c.execute("SELECT * FROM players WHERE minecraft_id = ?", (minecraft_id,))
    result = c.fetchall()
    try:
        return result[0]
    except IndexError:
        return False


def fetch_discord_id(discord_id):
    c.execute("SELECT * FROM players WHERE discord_id = ?", (discord_id,))
    result = c.fetchall()
    try:
        return result[0]
    except IndexError:
        return False


def fetch_minecraft_username(minecraft_username):
    c.execute("SELECT * FROM players WHERE minecraft_username = ?", (minecraft_username,))
    result = c.fetchall()
    try:
        return result[0]
    except IndexError:
        return False


class PlayerDoesNotExistError(Exception):
    """Exception raised when player is not in the database"""

    def __init__(self, message="Player does not exist in the database"):
        self.message = message
        super().__init__(self.message)


class Player:
    def __init__(self, identifier):
        data = ()
        if isinstance(identifier, str):
            if len(identifier) > 30:
                data = fetch_player_id(identifier)
            else:
                data = fetch_minecraft_username(identifier)
        elif isinstance(identifier, int):
            data = fetch_discord_id(identifier)

        if data:
            self.minecraft_id = data[0]
            self.discord_id = data[1]
            self.minecraft_username = data[2]
            self.priority = data[3]
            self.elo = data[4]
        else:
            raise PlayerDoesNotExistError()

    def update(self):
        data = fetch_player_id(self.minecraft_id)
        self.minecraft_username = data[2]
        self.priority = data[3]
        self.elo = data[4]

    def get_priority(self):
        self.update()
        return self.priority

    def set_priority(self, priority):
        if isinstance(priority, int):
            if priority < 0:
                return False
            c.execute("UPDATE players SET priority = ? WHERE minecraft_id = ?", (priority, self.minecraft_id))
            conn.commit()
            return True
        else:
            return False

    def change_priority(self, amount):
        if isinstance(amount, int):
            self.update()
            self.set_priority(self.priority + amount if self.priority + amount >= 0 else 0)
            return True
        else:
            return False

    def get_elo(self):
        self.update()
        return self.elo

    def set_elo(self, elo):
        if isinstance(elo, int):
            if elo < ELO_FLOOR:
                return False
            c.execute("UPDATE players SET elo = ? WHERE minecraft_id = ?", (elo, self.minecraft_id))
            conn.commit()
            return True
        else:
            return False

    def change_elo(self, amount):
        if isinstance(amount, int):
            self.update()
            self.set_elo(self.elo + amount if self.elo + amount >= ELO_FLOOR else ELO_FLOOR)
            return True
        else:
            return False

    def update_minecraft_username(self):
        self.minecraft_username = MojangAPI.get_username(self.minecraft_id)
        c.execute("UPDATE players SET minecraft_username = ? WHERE minecraft_id = ?",
                  (self.minecraft_username, self.minecraft_id))
        conn.commit()
        return self.minecraft_username

    def change_minecraft_username(self, minecraft_username):
        minecraft_id = MojangAPI.get_uuid(minecraft_username)
        if minecraft_id:
            old_minecraft_id = self.minecraft_id
            self.minecraft_id = minecraft_id
            self.minecraft_username = minecraft_username
            c.execute("UPDATE players SET minecraft_id = ?, minecraft_username = ? WHERE minecraft_id = ?",
                      (self.minecraft_id, self.minecraft_username, old_minecraft_id))
            conn.commit()
            return True
        else:
            return False
