from datetime import datetime, timedelta
from pytz import timezone

from database.database import check_events_event_id, fetch_events_event_id, add_event, fetch_events_list_event_id, \
    delete_event, update_events_title, update_events_description, update_events_time_est, update_events_num_can_play, \
    update_events_num_is_muted, update_events_num_can_sub


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
        self.signup_deadline = data[10]
        self.num_can_play = data[11]
        self.num_is_muted = data[12]
        self.num_can_sub = data[13]

    def delete(self):
        return delete_event(self.event_id)

    def update(self):
        data = fetch_events_event_id(self.event_id)
        self.title = data[1]
        self.description = data[2]
        self.time_est = data[3]
        self.signup_deadline = data[10]
        self.num_can_play = data[11]
        self.num_is_muted = data[12]
        self.num_can_sub = data[13]

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
            time_est = datetime.fromisoformat(time_est)
        except ValueError:
            raise ValueError
        current_date = datetime.now(timezone('EST'))
        td = time_est - current_date
        if td < timedelta(0):
            raise TimeBeforeCurrentTimeError()
        self.time_est = time_est
        update_events_time_est(time_est, self.event_id)
        return True

    def get_num_can_play(self):
        self.update()
        return self.num_can_play

    def set_num_can_play(self, num_can_play):
        if num_can_play < 0:
            return False
        update_events_num_can_play(num_can_play, self.event_id)
        return True

    def change_num_can_play(self, amount):
        self.update()
        num_can_play = self.num_can_play + amount
        self.set_num_can_play(num_can_play if num_can_play >= 0 else 0)

    def get_num_is_muted(self):
        self.update()
        return self.num_is_muted

    def set_num_is_muted(self, num_is_muted):
        if num_is_muted < 0:
            return False
        update_events_num_is_muted(num_is_muted, self.event_id)
        return True

    def change_num_is_muted(self, amount):
        self.update()
        num_is_muted = self.num_is_muted + amount
        self.set_num_is_muted(num_is_muted if num_is_muted >= 0 else 0)

    def get_num_can_sub(self):
        self.update()
        return self.num_can_sub

    def set_num_can_sub(self, num_can_sub):
        if num_can_sub < 0:
            return False
        update_events_num_can_sub(num_can_sub, self.event_id)
        return True

    def change_num_can_sub(self, amount):
        self.update()
        num_can_sub = self.num_can_sub + amount
        self.set_num_can_sub(num_can_sub if num_can_sub >= 0 else 0)

    @classmethod
    def add_event(cls, event_id, title, description, time_est, created_est, creator, guild, announcement_channel,
                  signup_channel, signup_message, signup_deadline):
        if check_events_event_id(event_id):
            raise EventAlreadyExistsError()
        add_event(event_id, title, description, time_est, created_est, creator, guild, announcement_channel,
                  signup_channel, signup_message, signup_deadline)
        return cls((event_id, title, description, time_est, created_est, creator, guild, announcement_channel,
                    signup_channel, signup_message, signup_deadline, 0, 0, 0, 0))

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

    @staticmethod
    def event_check(event_id):
        return check_events_event_id(event_id)
