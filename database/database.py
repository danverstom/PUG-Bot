import sqlite3 as sql

conn = sql.connect("database/database.db")

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

conn.execute(
    '''create table if not exists events (
    event_id integer,
    event_title text,
    event_description text,
    event_time_est blob,
    event_created_est blob,
    event_creator integer,
    guild_id integer,
    announcement_channel integer,
    signup_channel integer,
    signup_message integer,
    num_can_play integer,
    num_cant_play integer,
    num_is_muted integer,
    num_can_sub integer)'''
)

conn.execute(
    '''create table if not exists signups (
    user_id integer,
    event_id integer,
    is_playing bool,
    is_muted bool,
    can_sub bool)'''
)

conn.commit()
c = conn.cursor()

"""
Functions that interact with the Players database
"""


def add_player(minecraft_id, discord_id, minecraft_username, priority=0, elo=1000):
    if check_players_minecraft_id(minecraft_id):
        return False
    elif check_players_discord_id(discord_id):
        return False
    c.execute("INSERT INTO players VALUES (?,?,?,?,?)", (minecraft_id, discord_id, minecraft_username, priority, elo))
    conn.commit()
    return True


def delete_player(minecraft_id):
    if check_players_minecraft_id(minecraft_id):
        c.execute("DELETE FROM players WHERE minecraft_id = ?", (minecraft_id,))
        conn.commit()
        return True
    else:
        return False


def check_players_minecraft_id(minecraft_id):
    c.execute("SELECT minecraft_id FROM players WHERE minecraft_id = ?", (minecraft_id,))
    return bool(c.fetchone())


def check_players_discord_id(discord_id):
    c.execute("SELECT discord_id FROM players WHERE discord_id = ?", (discord_id,))
    return bool(c.fetchone())


def fetch_players_minecraft_id(minecraft_id):
    c.execute("SELECT * FROM players WHERE minecraft_id = ?", (minecraft_id,))
    return c.fetchone()


def fetch_players_discord_id(discord_id):
    c.execute("SELECT * FROM players WHERE discord_id = ?", (discord_id,))
    return c.fetchone()


def fetch_players_minecraft_username(minecraft_username):
    c.execute("SELECT * FROM players WHERE minecraft_username = ?", (minecraft_username,))
    return c.fetchone()


def fetch_players_list_discord_id():
    c.execute("SELECT discord_id FROM players")
    return c.fetchall()


def update_players_minecraft_id(new_minecraft_id, minecraft_username, old_minecraft_id):
    c.execute("UPDATE players SET minecraft_id = ?, minecraft_username = ? WHERE minecraft_id = ?",
              (new_minecraft_id, minecraft_username, old_minecraft_id))
    conn.commit()


def update_players_discord_id(discord_id, minecraft_id):
    c.execute("UPDATE players SET discord_id = ? WHERE minecraft_id = ?", (discord_id, minecraft_id))
    conn.commit()


def update_players_minecraft_username(minecraft_username, minecraft_id):
    c.execute("UPDATE players SET minecraft_username = ? WHERE minecraft_id = ?", (minecraft_username, minecraft_id))
    conn.commit()


def update_players_elo(elo, minecraft_id):
    c.execute("UPDATE players SET elo = ? WHERE minecraft_id = ?", (elo, minecraft_id))
    conn.commit()


def update_players_priority(priority, minecraft_id):
    c.execute("UPDATE players SET priority = ? WHERE minecraft_id = ?", (priority, minecraft_id))
    conn.commit()


def player_check(minecraft_id, discord_id):
    if check_players_minecraft_id(minecraft_id):
        return 1
    elif check_players_discord_id(discord_id):
        return 2
    else:
        return 0


"""
Functions that interact with the Register Requests database.
"""


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


def check_event_id(event_id):
    c.execute('select event_id from events where event_id = ?', (event_id,))
    result = c.fetchone()
    return bool(result)


def get_event_id(event_id):
    c.execute('select * from events where event_id = ?', (event_id,))
    return c.fetchone()


class EventDoesNotExist(Exception):
    """Exception raised when event is not in the database"""

    def __init__(self, message="Event does not exist in the database"):
        self.message = message
        super().__init__(self.message)


class Event:
    def __init__(self, event_id):
        if not check_event_id(event_id):
            raise EventDoesNotExist()

        event = get_event_id(event_id)
        self.event_id = event_id
        self.event_title = event[1]
        self.event_description = event[2]
        self.event_time_est = event[3]
        self.event_created_est = event[4]
        self.event_creator = event[5]
        self.guild_id = event[6]
        self.announcement_channel = event[7]
        self.signup_channel = event[8]
        self.signup_message = event[9]
        self.num_can_play = event[10]
        self.num_cant_play = event[11]
        self.num_is_muted = event[12]
        self.num_can_sub = event[13]

    @staticmethod
    def get_events():
        c.execute("SELECT * FROM events")
        return c.fetchall()
