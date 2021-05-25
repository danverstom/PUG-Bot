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

def get_active_strikes(user_id):
    c.execute("SELECT * FROM strikes WHERE user_id = ? AND is_active = 1", (user_id,))
    return c.fetchall()

def get_inactive_strikes(user_id):
    c.execute("SELECT * FROM strikes WHERE user_id = ? AND is_active = 0", (user_id,))
    return c.fetchall()

def get_all_strikes(user_id):
    c.execute("SELECT * FROM strikes WHERE user_id = ?", (user_id,))
    return c.fetchall()

def get_strike(id):
    c.execute("SELECT * FROM strikes WHERE strike_id = ?", (id,))
    return c.fetchone()

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
