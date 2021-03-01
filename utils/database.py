import sqlite3 as sql

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
    c.execute("SELECT * FROM players WHERE current_username = ?", (minecraft_username,))
    result = c.fetchall()
    try:
        return result[0]
    except IndexError:
        return False
