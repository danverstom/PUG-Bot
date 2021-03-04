import sqlite3 as sql
from mojang.api import MojangAPI
from utils.config import ELO_FLOOR

conn = sql.connect("utils/database.db")

conn.execute(
    '''create table if not exists players (
    minecraft_id text,
    discord_id integer,
    minecraft_username text, 
    priority integer,
    elo integer)''')

conn.execute(
    '''create table if not exists register_requests (
    minecraft_id text,
    discord_id integer,
    minecraft_username text,
    approval_embed_id integer)''')

conn.commit()
c = conn.cursor()


def add_register_request(minecraft_id, discord_id, minecraft_username, approval_embed_id):
    c.execute("INSERT INTO register_requests VALUES (?,?,?,?)", (minecraft_id, discord_id, minecraft_username,
                                                                 approval_embed_id))
    conn.commit()
    return True


def remove_register_request(approval_embed_id):
    c.execute("DELETE FROM register_requests WHERE approval_embed_id = ?", (approval_embed_id,))
    conn.commit()
    return True


def check_user_requests(discord_id):
    c.execute('select discord_id from register_requests where discord_id = ?', (discord_id,))
    result = c.fetchone()
    return bool(result)


def get_register_request(approval_embed_id):
    c.execute('select * from register_requests where approval_embed_id = ?', (approval_embed_id,))
    result = c.fetchone()
    return result


def get_all_register_requests():
    c.execute('select * from register_requests')
    result = c.fetchall()
    return result


def player_check(minecraft_id, discord_id):
    if fetch_players_minecraft_id(minecraft_id):
        return 1
    elif fetch_players_discord_id(discord_id):
        return 2
    else:
        return 0


def add_player(minecraft_id, discord_id, minecraft_username, priority=0, elo=1000):
    if fetch_players_minecraft_id(minecraft_id):
        return 1
    elif fetch_players_discord_id(discord_id):
        return 2
    c.execute("INSERT INTO players VALUES (?,?,?,?,?)", (minecraft_id, discord_id, minecraft_username, priority, elo))
    conn.commit()
    return 0


def delete_player(minecraft_id):
    if fetch_players_minecraft_id(minecraft_id):
        c.execute("DELETE FROM players WHERE minecraft_id = ?", (minecraft_id,))
        conn.commit()
        return True
    else:
        return False


def fetch_players_minecraft_id(minecraft_id):
    c.execute("SELECT * FROM players WHERE minecraft_id = ?", (minecraft_id,))
    result = c.fetchall()
    try:
        return result[0]
    except IndexError:
        return False


def fetch_players_discord_id(discord_id):
    c.execute("SELECT * FROM players WHERE discord_id = ?", (discord_id,))
    result = c.fetchall()
    try:
        return result[0]
    except IndexError:
        return False


def fetch_players_minecraft_username(minecraft_username):
    c.execute("SELECT * FROM players WHERE minecraft_username = ?", (minecraft_username,))
    result = c.fetchall()
    try:
        return result[0]
    except IndexError:
        return False


def fetch_players_list():
    c.execute("SELECT discord_id FROM players")
    result = c.fetchall()
    player_list = []
    for id_tuple in result:
        player_list.append(Player(id_tuple[0]))
    return player_list


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
                data = fetch_players_minecraft_id(identifier)
            else:
                data = fetch_players_minecraft_username(identifier)
        elif isinstance(identifier, int):
            data = fetch_players_discord_id(identifier)

        if data:
            self.minecraft_id = data[0]
            self.discord_id = data[1]
            self.minecraft_username = data[2]
            self.priority = data[3]
            self.elo = data[4]
        else:
            raise PlayerDoesNotExistError()

    def update(self):
        data = fetch_players_minecraft_id(self.minecraft_id)
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
            self.priority = priority
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
            self.elo = elo
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
            if fetch_players_minecraft_id(minecraft_id):
                return 1
            c.execute("UPDATE players SET minecraft_id = ?, minecraft_username = ? WHERE minecraft_id = ?",
                      (minecraft_id, minecraft_username, self.minecraft_id))
            conn.commit()
            self.minecraft_id = minecraft_id
            self.minecraft_username = minecraft_username
            return 0
        else:
            return 2

    def change_discord_id(self, discord_id):
        if fetch_players_discord_id(discord_id):
            return False
        c.execute("UPDATE players SET discord_id = ? WHERE discord_id = ?", (discord_id, self.discord_id))
        conn.commit()
        self.discord_id = discord_id
        return True
