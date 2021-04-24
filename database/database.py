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
    title text,
    description text,
    time_est blob,
    created_est blob,
    creator integer,
    guild_id integer,
    announcement_channel integer,
    signup_channel integer,
    signup_message integer,
    signup_role integer,
    signup_deadline integer,
    is_active bool,
    is_signup_active bool)'''
)

conn.execute(
    '''create table if not exists signups (
    user_id integer,
    event_id integer,
    can_play bool,
    is_muted bool,
    can_sub bool)'''
)

conn.execute(
    '''create table if not exists pug_events (
    pug_id integer primary key autoincrement,
    event_id integer,
    leader_one integer,
    leader_two integer,
    team_one_role integer,
    team_two_role integer,
    teams_drafted bool,
    in_progress bool,
    team_one_maps_won integer,
    team_two_maps_won integer,
    total_maps_played integer
    )
    '''
)

conn.execute(
    '''create table if not exists pug_draft (
    pug_id integer,
    discord_id integer,
    leader_id integer,
    team_role integer,
    draft_position integer
    )
    '''
)


conn.commit()
c = conn.cursor()

"""
Functions that interact with the PUG Draft table
"""


def is_player_drafted(pug_id, discord_id):
    c.execute("SELECT * FROM pug_draft WHERE pug_id = ? and discord_id = ?", (pug_id, discord_id))
    result = c.fetchall()
    if result:
        return True
    else:
        return False


def get_drafted_players_pug_id(pug_id):
    c.execute("SELECT * FROM pug_draft WHERE pug_id = ?", (pug_id,))
    result = c.fetchall()
    return result


def draft_player_pug(pug_id, discord_id, leader_id, team_role, draft_position):
    if not is_player_drafted(pug_id, discord_id):
        c.execute("INSERT INTO pug_draft ("
                  "pug_id,"
                  "discord_id,"
                  "leader_id,"
                  "team_role,"
                  "draft_position) "
                  "VALUES (?,?,?,?,?)",
                  (pug_id, discord_id, leader_id, team_role, draft_position))
        conn.commit()
        return True
    else:
        return False


def undraft_player_pug(pug_id, discord_id):
    if is_player_drafted(pug_id, discord_id):
        c.execute("DELETE FROM pug_draft WHERE pug_id = ? and discord_id = ?", (pug_id,discord_id))
        conn.commit()
        return True
    else:
        return False


"""
Functions that interact with the PUG Events table
"""


def pug_event_exists_event_id(event_id):
    """Check to see if a PUG event has been created for an event"""
    c.execute("SELECT * FROM pug_events WHERE event_id = ?", (event_id,))
    result = c.fetchall()
    if result:
        return True
    else:
        return False


def pug_event_exists_pug_id(pug_id):
    c.execute("SELECT * FROM pug_events WHERE pug_id = ?", (pug_id,))
    result = c.fetchall()
    if result:
        return True
    else:
        return False


def get_pug_event_from_pug_id(pug_id):
    c.execute("SELECT * FROM pug_events WHERE pug_id = ?", (pug_id,))
    result = c.fetchall()
    return result


def get_pug_event_from_event_id(event_id):
    c.execute("SELECT * FROM pug_events WHERE event_id = ?", (event_id,))
    result = c.fetchall()
    return result


def create_pug_event(event_id, leader_one, leader_two, team_one_role, team_two_role):
    if not pug_event_exists_event_id(event_id):
        c.execute("INSERT INTO pug_events (event_id, "
                  "leader_one,"
                  "leader_two,"
                  "team_one_role,"
                  "team_two_role,"
                  "teams_drafted,"
                  "in_progress,"
                  "team_one_maps_won,"
                  "team_two_maps_won,"
                  "total_maps_played)"
                  "VALUES (?,?,?,?,?,?,?,?,?,?)", (
                      event_id, leader_one, leader_two, team_one_role, team_two_role, False, False, 0, 0, 0
                  ))
        conn.commit()
        return True
    else:
        # PUG Event already exists for this event
        return False


def delete_pug_event(pug_id):
    if pug_event_exists_pug_id(pug_id):
        c.execute("DELETE FROM pug_events WHERE pug_id = ?", (pug_id,))
        conn.commit()
        return True
    else:
        return False


def set_pug_event_teams_drafted(pug_id, value: bool):
    c.execute("UPDATE pug_events SET teams_drafted = ? WHERE pug_id = ?", (value, pug_id))
    conn.commit()
    return True


def set_pug_event_in_progress(pug_id, value: bool):
    c.execute("UPDATE pug_events SET in_progress = ? WHERE pug_id = ?", (value, pug_id))
    conn.commit()
    return True


def set_pug_event_team_one_maps_won(pug_id, value: bool):
    c.execute("UPDATE pug_events SET team_one_maps_won = ? WHERE pug_id = ?", (value, pug_id))
    conn.commit()
    return True


def set_pug_event_team_two_maps_won(pug_id, value: bool):
    c.execute("UPDATE pug_events SET team_two_maps_won = ? WHERE pug_id = ?", (value, pug_id))
    conn.commit()
    return True


def set_pug_event_total_maps_played(pug_id, value: bool):
    c.execute("UPDATE pug_events SET total_maps_played = ? WHERE pug_id = ?", (value, pug_id))
    conn.commit()
    return True



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


def get_sorted_elo():
    c.execute("SELECT minecraft_username, elo, discord_id FROM players ORDER BY elo DESC")
    return c.fetchall()


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


"""
Functions that interact with the Events database.
"""


def add_event(event_id, title, description, time_est, created_est, creator, guild_id, announcement_channel,
              signup_channel, signup_message, signup_role, signup_deadline, is_active=1, is_signup_active=1):
    if check_events_event_id(event_id):
        return False
    c.execute("INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
              (event_id, title, description, time_est, created_est, creator, guild_id, announcement_channel,
               signup_channel, signup_message, signup_role, signup_deadline, is_active, is_signup_active))
    conn.commit()
    return True


def delete_event(event_id):
    if check_events_event_id(event_id):
        c.execute("DELETE FROM events WHERE event_id = ?", (event_id,))
        conn.commit()
        return True
    else:
        return False


def check_events_event_id(event_id):
    c.execute('SELECT event_id FROM events WHERE event_id = ?', (event_id,))
    return bool(c.fetchone())


def fetch_events_event_id(event_id):
    c.execute('SELECT * FROM events WHERE event_id = ?', (event_id,))
    return c.fetchone()


def fetch_events_list_event_id():
    c.execute("SELECT event_id FROM events")
    return c.fetchall()


def fetch_active_events_list_event_id():
    c.execute("SELECT event_id FROM events WHERE is_active = 1")
    return c.fetchall()


def fetch_signup_active_events_list_event_id():
    c.execute("SELECT event_id FROM events WHERE is_signup_active = 1")
    return c.fetchall()


def update_events_title(title, event_id):
    c.execute("UPDATE events SET title = ? WHERE event_id = ?", (title, event_id))
    conn.commit()


def update_events_description(description, event_id):
    c.execute("UPDATE events SET description = ? WHERE event_id = ?", (description, event_id))
    conn.commit()


def update_events_time_est(time_est, event_id):
    c.execute("UPDATE events SET time_est = ? WHERE event_id = ?", (time_est, event_id))
    conn.commit()


def update_events_signup_deadline(signup_deadline, event_id):
    c.execute("UPDATE events SET signup_deadline = ? WHERE event_id = ?", (signup_deadline, event_id))
    conn.commit()


def update_events_is_active(is_active, event_id):
    c.execute("UPDATE events SET is_active = ? WHERE event_id = ?", (is_active, event_id))
    conn.commit()


def update_events_is_signup_active(is_signup_active, event_id):
    c.execute("UPDATE events SET is_signup_active = ? WHERE event_id = ?", (is_signup_active, event_id))
    conn.commit()


"""
Functions that interact with the Events database.
"""


def add_signup(user_id, event_id, can_play=0, is_muted=0, can_sub=0):
    if check_signups_user_event(user_id, event_id):
        return False
    c.execute("INSERT INTO signups VALUES (?, ?, ?, ?, ?)", (user_id, event_id, can_play, is_muted, can_sub))
    conn.commit()
    return True


def delete_signup(user_id, event_id):
    if check_signups_user_event(user_id, event_id):
        c.execute("DELETE FROM signups WHERE user_id = ? AND event_id = ?", (user_id, event_id))
        conn.commit()
        return True
    else:
        return False


def check_signups_user_event(user_id, event_id):
    c.execute("SELECT user_id FROM signups WHERE user_id = ? AND event_id = ?", (user_id, event_id))
    return bool(c.fetchone())


def fetch_signups_user_event(user_id, event_id):
    c.execute("SELECT * FROM signups WHERE user_id = ? AND event_id = ?", (user_id, event_id))
    return c.fetchone()


def fetch_signups_list_event_id(event_id):
    c.execute("SELECT user_id, event_id FROM signups WHERE event_id = ?", (event_id,))
    return c.fetchall()


def update_signups_can_play(can_play, user_id, event_id):
    c.execute("UPDATE signups SET can_play = ? WHERE user_id = ? AND event_id = ?", (can_play, user_id, event_id))
    conn.commit()


def update_signups_is_muted(is_muted, user_id, event_id):
    c.execute("UPDATE signups SET is_muted = ? WHERE user_id = ? AND event_id = ?", (is_muted, user_id, event_id))
    conn.commit()


def update_signups_can_sub(can_sub, user_id, event_id):
    c.execute("UPDATE signups SET can_sub = ? WHERE user_id = ? AND event_id = ?", (can_sub, user_id, event_id))
    conn.commit()
