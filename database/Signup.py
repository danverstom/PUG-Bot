from database.database import add_signup, check_signups_user_event, fetch_signups_user_event, \
    fetch_signups_list_event_id, delete_signup, update_signups_can_play, update_signups_is_muted, update_signups_can_sub
from database.strikes import get_active_user_strikes

class SignupAlreadyExistsError(Exception):
    """Exception raised when signup is already in the database"""

    def __init__(self, message="Signup already exists in the database"):
        self.message = message
        super().__init__(self.message)


class SignupDoesNotExistError(Exception):
    """Exception raised when signup is not in the database"""

    def __init__(self, message="Signup does not exist in the database"):
        self.message = message
        super().__init__(self.message)


class Signup:
    def __init__(self, data):
        if not data or not isinstance(data, tuple):
            raise ValueError
        self.user_id = data[0]
        self.event_id = data[1]
        self.can_play = bool(data[2])
        self.is_muted = bool(data[3])
        self.can_sub = bool(data[4])

    def __eq__(self, other):
        if isinstance(other, Signup):
            return self.user_id == other.user_id and self.event_id == other.event_id
        else:
            return False

    def delete(self):
        return delete_signup(self.user_id, self.event_id)

    def update(self):
        data = fetch_signups_user_event(self.user_id, self.event_id)
        self.can_play = bool(data[2])
        self.is_muted = bool(data[3])
        self.can_sub = bool(data[4])

    def update_db(self):
        if check_signups_user_event(int(self.user_id), self.event_id):
            update_signups_can_play(int(self.can_play), self.user_id, self.event_id)
            update_signups_is_muted(int(self.is_muted), self.user_id, self.event_id)
            update_signups_can_sub(int(self.can_sub), self.user_id, self.event_id)
        else:
            add_signup(self.user_id, self.event_id, int(self.can_play), int(self.is_muted), int(self.can_sub))

    def set_can_play(self, can_play):
        self.can_play = can_play
        update_signups_can_play(int(can_play), self.user_id, self.event_id)
        return True

    def set_is_muted(self, is_muted):
        self.is_muted = is_muted
        update_signups_is_muted(int(is_muted), self.user_id, self.event_id)
        return True

    def set_can_sub(self, can_sub):
        self.can_sub = can_sub
        update_signups_can_sub(int(can_sub), self.user_id, self.event_id)
        return True

    def is_unsigned(self):
        return not self.can_play and not self.can_sub

    def is_striked(self):
        return bool(get_active_user_strikes(self.user_id))

    @classmethod
    def create_signup(cls, user_id, event_id, can_play=False, is_muted=False, can_sub=False):
        return cls((user_id, event_id, can_play, is_muted, can_sub))

    @classmethod
    def add_signup(cls, user_id, event_id, can_play=False, is_muted=False, can_sub=False):
        if check_signups_user_event(user_id, event_id):
            raise SignupAlreadyExistsError()
        add_signup(user_id, event_id, int(can_play), int(is_muted), int(can_sub))
        return cls((user_id, event_id, can_play, is_muted, can_sub))

    @classmethod
    def from_user_event(cls, user_id, event_id):
        data = fetch_signups_user_event(user_id, event_id)
        if data:
            return cls(data)
        else:
            raise SignupDoesNotExistError()

    @classmethod
    def fetch_signups_list(cls, event_id):
        result = fetch_signups_list_event_id(event_id)
        signup_list = []
        for id_tuple in result:
            signup_list.append(cls.from_user_event(id_tuple[0], id_tuple[1]))
        return signup_list

    @staticmethod
    def signup_check(user_id, event_id):
        return check_signups_user_event(user_id, event_id)
