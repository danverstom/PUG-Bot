from database.database import conn
from datetime import datetime
from pytz import timezone
from utils.config import *

conn.execute(
    '''
    create table if not exists referrals (
        referral_id integer primary key autoincrement,
        code text,
        user_joined_id integer,
        inviter_id integer,
        joined_at blob,
        has_user_played bool,
        reward_given bool
    )
    '''
)

conn.commit()
c = conn.cursor()

def log_referral(code, user_joined_id, inviter_id):
    if is_user_referred(user_joined_id):
        return False
    c.execute(
        '''
        INSERT INTO referrals (
            code,
            user_joined_id,
            inviter_id,
            joined_at,
            has_user_played,
            reward_given
        ) VALUES (?,?,?,?,?,?)
        ''',
        (
            code, 
            user_joined_id, 
            inviter_id,
            datetime.now(timezone(TIMEZONE)).isoformat(),
            False,
            False
        )
    )
    conn.commit()
    return True

def update_referral(referral_id, column_name, value):
    c.execute(f"UPDATE referrals SET {column_name} = ? WHERE referral_id = ?", (value, referral_id))
    conn.commit()

def get_all_referrals():
    c.execute("SELECT * FROM referrals")
    return c.fetchall()

def get_filtered_referrals(variable_name, value):
    c.execute(f"SELECT * FROM referrals WHERE {variable_name} = ?", (value,))
    return c.fetchall()

def get_unrewarded_referrals(inviter_id):
    c.execute(f"SELECT * FROM referrals WHERE inviter_id = ? AND reward_given = 0", (inviter_id,))
    return c.fetchall()

def mark_all_referrals_awarded(inviter_id):
    c.execute("UPDATE referrals SET reward_given = 1 WHERE inviter_id = ?", (inviter_id,))
    conn.commit()


def is_user_referred(user_joined_id):
    return bool(get_filtered_referrals("user_joined_id", user_joined_id))