from database.database import conn
from datetime import datetime
from pytz import timezone
from utils.config import *

conn.execute(
    '''
    create table if not exists referrals (
        code text,
        user_joined_id integer,
        inviter_id integer,
        joined_at blob,
        has_user_played bool
    )
    '''
)

conn.commit()
c = conn.cursor()

def log_referral(code, user_joined_id, inviter_id):
    c.execute(
        '''
        INSERT INTO referrals (
            code,
            user_joined_id,
            inviter_id,
            joined_at,
            has_user_played
        ) VALUES (?,?,?,?,?)
        ''',
        (
            code, 
            user_joined_id, 
            inviter_id,
            datetime.now(timezone(TIMEZONE)).isoformat(),
            False
        )
    )
    conn.commit()
    return True