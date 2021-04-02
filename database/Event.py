from datetime import datetime, timedelta
from pytz import timezone
from utils.config import TIMEZONE
from database.database import check_events_event_id, fetch_events_event_id, add_event, fetch_events_list_event_id, \
    delete_event, update_events_title, update_events_description, update_events_time_est, \
    update_events_signup_deadline, update_events_is_active, fetch_active_events_list_event_id, \
    update_events_is_signup_active, fetch_signup_active_events_list_event_id


class EventDoesNotExistError(Exception):
    """Exception raised when event is not in the database"""

    def __init__(self, message="Event does not exist in the database"):
        self.message = message
        super().__init__(self.message)


class EventAlreadyExistsError(Exception):
    """Exception raised when event is already in the database"""

    def __init__(self, message="Event already exists in the database"):
        self.message = message
        super().__init__(self.message)


class TimeBeforeCurrentTimeError(Exception):
    """Exception raised when inputted time is before the current time"""

    def __init__(self, message="Time is before the current time"):
        self.message = message
        super().__init__(self.message)


class Event:
    def __init__(self, data):
        if not data or not isinstance(data, tuple):
            raise ValueError
        self.event_id = data[0]
        self.title = data[1]
        self.description = data[2]
        self.time_est = data[3]
        self.created_est = data[4]
        self.creator = data[5]
        self.guild_id = data[6]
        self.announcement_channel = data[7]
        self.signup_channel = data[8]
        self.signup_message = data[9]
        self.signup_role = data[10]
        self.signup_deadline = data[11]
        self.is_active = bool(data[12])
        self.is_signups_active = bool(data[13])

    def delete(self):
        return delete_event(self.event_id)

    def update(self):
        data = fetch_events_event_id(self.event_id)
        self.title = data[1]
        self.description = data[2]
        self.time_est = data[3]
        self.signup_deadline = data[11]
        self.is_active = bool(data[12])
        self.is_signups_active = bool(data[13])

    def get_title(self):
        self.update()
        return self.title

    def set_title(self, title):
        self.title = title
        update_events_title(title, self.event_id)
        return True

    def get_description(self):
        self.update()
        return self.description

    def set_description(self, description):
        self.description = description
        update_events_description(description, self.event_id)
        return True

    def get_event_time_est(self):
        self.update()
        return self.time_est

    def set_event_time_est(self, time_est):
        try:
            datetime_est = datetime.fromisoformat(time_est)
        except ValueError:
            raise ValueError
        current_date = datetime.now(timezone(TIMEZONE))
        if datetime_est < current_date:
            raise TimeBeforeCurrentTimeError()
        self.time_est = time_est
        update_events_time_est(time_est, self.event_id)
        return True

    def get_signup_deadline(self):
        self.update()
        return self.signup_deadline

    def set_signup_deadline(self, signup_deadline):
        try:
            datetime_signup_deadline = datetime.fromisoformat(signup_deadline)
        except ValueError:
            raise ValueError
        current_date = datetime.now(timezone(TIMEZONE))
        if datetime_signup_deadline < current_date:
            raise TimeBeforeCurrentTimeError()
        self.signup_deadline = signup_deadline
        update_events_signup_deadline(signup_deadline, self.event_id)
        return True

    def postpone(self, amount):
        event_time = datetime.fromisoformat(self.time_est)
        signup_deadline = datetime.fromisoformat(self.signup_deadline)
        change_amount = timedelta(minutes=amount)
        self.set_event_time_est((event_time + change_amount).isoformat())
        self.set_signup_deadline((signup_deadline + change_amount).isoformat())

    def get_is_active(self):
        self.update()
        return self.is_active

    def set_is_active(self, is_active):
        self.is_active = is_active
        update_events_is_active(int(is_active), self.event_id)
        return True

    def get_is_signup_active(self):
        self.update()
        return self.is_signups_active

    def set_is_signup_active(self, is_signup_active):
        self.is_signups_active = is_signup_active
        update_events_is_signup_active(int(is_signup_active), self.event_id)
        return True

    @classmethod
    def add_event(cls, event_id, title, description, time_est, created_est, creator, guild, announcement_channel,
                  signup_channel, signup_message, signup_role, signup_deadline):
        if check_events_event_id(event_id):
            raise EventAlreadyExistsError()
        add_event(event_id, title, description, time_est, created_est, creator, guild, announcement_channel,
                  signup_channel, signup_message, signup_role, signup_deadline)
        return cls((event_id, title, description, time_est, created_est, creator, guild, announcement_channel,
                    signup_channel, signup_message, signup_role, signup_deadline, True, True))

    @classmethod
    def from_event_id(cls, event_id):
        data = fetch_events_event_id(event_id)
        if data:
            return cls(data)
        else:
            raise EventDoesNotExistError()

    @classmethod
    def fetch_events_list(cls):
        result = fetch_events_list_event_id()
        event_list = []
        for id_tuple in result:
            event_list.append(cls.from_event_id(id_tuple[0]))
        return event_list

    @classmethod
    def fetch_events_dict(cls):
        result = fetch_events_list_event_id()
        event_dict = dict()
        for id_tuple in result:
            event_dict[id_tuple[0]] = cls.from_event_id(id_tuple[0])
        return event_dict

    @classmethod
    def fetch_active_events_list(cls):
        result = fetch_active_events_list_event_id()
        event_list = []
        for id_tuple in result:
            event_list.append(cls.from_event_id(id_tuple[0]))
        return event_list

    @classmethod
    def fetch_active_events_dict(cls):
        result = fetch_active_events_list_event_id()
        event_dict = dict()
        for id_tuple in result:
            event_dict[id_tuple[0]] = cls.from_event_id(id_tuple[0])
        return event_dict

    @classmethod
    def fetch_signup_active_events_list(cls):
        result = fetch_signup_active_events_list_event_id()
        event_list = []
        for id_tuple in result:
            event_list.append(cls.from_event_id(id_tuple[0]))
        return event_list

    @classmethod
    def fetch_signup_active_events_dict(cls):
        result = fetch_signup_active_events_list_event_id()
        event_dict = dict()
        for id_tuple in result:
            event_dict[id_tuple[0]] = cls.from_event_id(id_tuple[0])
        return event_dict

    @staticmethod
    def event_check(event_id):
        return check_events_event_id(event_id)
