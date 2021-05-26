from mojang import MojangAPI
from random import choice, seed

from utils.config import ELO_FLOOR
from database.database import fetch_players_minecraft_id, fetch_players_minecraft_username, fetch_players_discord_id, \
    fetch_players_list_discord_id, update_players_priority, update_players_elo, update_players_minecraft_username, \
    update_players_minecraft_id, update_players_discord_id, check_players_minecraft_id, check_players_discord_id, \
    add_player, delete_player, player_check
from database.strikes import get_active_user_strikes



class PlayerDoesNotExistError(Exception):
    """Exception raised when player is not in the database"""

    def __init__(self, message="Player does not exist in the database"):
        self.message = message
        super().__init__(self.message)


class UsernameDoesNotExistError(Exception):
    """Exception raised when a username is not a valid Minecraft username"""

    def __init__(self, message="Username is not a valid Minecraft username"):
        self.message = message
        super().__init__(self.message)


class UsernameAlreadyExistsError(Exception):
    """Exception raised when a username being inputted into the database already exists"""

    def __init__(self, message="Username already exists in the database"):
        self.message = message
        super().__init__(self.message)


class DiscordAlreadyExistsError(Exception):
    """Exception raised when a discord id being inputted into the database already exists"""

    def __init__(self, message="Discord user already exists in the database"):
        self.message = message
        super().__init__(self.message)


class Player:
    def __init__(self, data):
        if not data or not isinstance(data, tuple):
            raise ValueError
        self.minecraft_id = data[0]
        self.discord_id = data[1]
        self.minecraft_username = data[2]
        self.priority = data[3]
        self.elo = data[4]

    def delete(self):
        return delete_player(self.minecraft_id)

    def update(self):
        data = fetch_players_minecraft_id(self.minecraft_id)
        self.minecraft_username = data[2]
        self.priority = data[3]
        self.elo = data[4]

    def get_priority(self):
        self.update()
        return self.priority

    def set_priority(self, priority):
        if priority < 0:
            return False
        self.priority = priority
        update_players_priority(priority, self.minecraft_id)
        return True

    def change_priority(self, amount):
        self.update()
        self.set_priority(self.priority + amount if self.priority + amount >= 0 else 0)

    def get_elo(self):
        self.update()
        return self.elo

    def set_elo(self, elo):
        if elo < ELO_FLOOR:
            return False
        self.elo = elo
        update_players_elo(elo, self.minecraft_id)
        return True

    def change_elo(self, amount):
        self.update()
        self.set_elo(self.elo + amount if self.elo + amount >= ELO_FLOOR else ELO_FLOOR)

    def update_minecraft_username(self):
        self.minecraft_username = MojangAPI.get_username(self.minecraft_id)
        update_players_minecraft_username(self.minecraft_username, self.minecraft_id)
        return self.minecraft_username

    def change_minecraft_username(self, minecraft_username):
        minecraft_id = MojangAPI.get_uuid(minecraft_username)
        if minecraft_id:
            if fetch_players_minecraft_id(minecraft_id):
                raise UsernameAlreadyExistsError(f"Username {minecraft_username} already exists in the database")
            update_players_minecraft_id(minecraft_id, minecraft_username, self.minecraft_id)
            self.minecraft_id = minecraft_id
            self.minecraft_username = minecraft_username
            return True
        else:
            raise UsernameDoesNotExistError(f"Username {minecraft_username} is not a valid Minecraft username")

    def change_discord_id(self, discord_id):
        if fetch_players_discord_id(discord_id):
            raise DiscordAlreadyExistsError(f"Discord {discord_id} already exists in the database")
        update_players_discord_id(discord_id, self.minecraft_id)
        self.discord_id = discord_id
        return True

    def is_striked(self):
        return bool(get_active_user_strikes(self.discord_id))

    @classmethod
    def add_player(cls, minecraft_id, discord_id, priority=0, elo=1000):
        minecraft_username = MojangAPI.get_username(minecraft_id)
        if minecraft_username:
            if check_players_minecraft_id(minecraft_id):
                raise UsernameAlreadyExistsError()
            elif check_players_discord_id(discord_id):
                raise DiscordAlreadyExistsError()
            add_player(minecraft_id, discord_id, minecraft_username, priority, elo)
            return cls((minecraft_id, discord_id, minecraft_username, priority, elo))
        else:
            raise UsernameDoesNotExistError()

    @classmethod
    def from_minecraft_id(cls, minecraft_id):
        data = fetch_players_minecraft_id(minecraft_id)
        if data:
            return cls(data)
        else:
            raise PlayerDoesNotExistError()

    @classmethod
    def from_minecraft_username(cls, minecraft_username):
        data = fetch_players_minecraft_username(minecraft_username)
        if data:
            return cls(data)
        else:
            raise PlayerDoesNotExistError()

    @classmethod
    def from_discord_id(cls, discord_id):
        data = fetch_players_discord_id(discord_id)
        if data:
            return cls(data)
        else:
            raise PlayerDoesNotExistError()

    @classmethod
    def exists_discord_id(cls, discord_id):
        data = fetch_players_discord_id(discord_id)
        if data:
            return cls(data)
        else:
            return False

    @classmethod
    def fetch_players_list(cls):
        result = fetch_players_list_discord_id()
        player_list = []
        for id_tuple in result:
            player_list.append(cls.from_discord_id(id_tuple[0]))
        return player_list

    @staticmethod
    def player_check(minecraft_id, discord_id):
        return player_check(minecraft_id, discord_id)

    @classmethod
    def fetch_random_player(cls):
        seed()
        return choice(Player.fetch_players_list())

