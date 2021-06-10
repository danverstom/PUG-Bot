from database.database import conn

conn.execute(
    '''
    create table if not exists strikes (
        strike_id integer primary key autoincrement,
        user_id integer,
        striked_by integer,
        striked_at blob,
        expiry_date blob,
        strike_reason text,
        is_active bool
    )
    '''
)

conn.commit()
c = conn.cursor()

def get_active_user_strikes(user_id):
    c.execute("SELECT * FROM strikes WHERE user_id = ? AND is_active = 1", (user_id,))
    return c.fetchall()

def get_inactive_user_strikes(user_id):
    c.execute("SELECT * FROM strikes WHERE user_id = ? AND is_active = 0", (user_id,))
    return c.fetchall()

def get_all_user_strikes(user_id):
    c.execute("SELECT * FROM strikes WHERE user_id = ?", (user_id,))
    return c.fetchall()

def get_all_strikes():
    c.execute("SELECT * FROM strikes")
    return c.fetchall()

def get_all_active_strikes():
    c.execute("SELECT * FROM strikes WHERE is_active = 1")
    return c.fetchall()

def get_all_inactive_strikes():
    c.execute("SELECT * FROM strikes WHERE is_active = 0")
    return c.fetchall()

def get_strike(id):
    c.execute("SELECT * FROM strikes WHERE strike_id = ?", (id,))
    return c.fetchone()

def change_active_status(id, status):
    c.execute("UPDATE strikes SET is_active = ? WHERE strike_id = ?", (status, id))
    conn.commit()

def add_strike(user_id, striked_by, striked_at, expiry_date, strike_reason):
    c.execute(
        '''
        INSERT INTO strikes (
            user_id,
            striked_by,
            striked_at,
            expiry_date,
            strike_reason,
            is_active
        ) 
        VALUES (?,?,?,?,?,?)
        ''',
        (
            user_id, striked_by, striked_at, expiry_date, strike_reason, True
        )
    )
    conn.commit()
    return True

def remove_strike(strike_id):
    if get_strike(strike_id):
        c.execute(
            '''
            DELETE FROM strikes WHERE strike_id = ?
            ''',
            (strike_id,)
        )
        conn.commit()
        return True
    else:
        return False
