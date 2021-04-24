from database.database import *
from database.Player import Player, PlayerDoesNotExistError
from logging import info


class PUGEventDoesNotExistError(Exception):
    """Exception raised when a PUG event is not in the database"""

    def __init__(self, message="This PUG event does not exist in the database"):
        self.message = message
        super().__init__(self.message)


class PUGEventAlreadyExistsError(Exception):
    """Exception raised when a PUG event is already in the database"""

    def __init__(self, message="Event already exists in the database"):
        self.message = message
        super().__init__(self.message)


class PlayerAlreadyDraftedError(Exception):
    """Exception raised when a player is already drafted for a PUG"""

    def __init__(self, message="This player has already been drafted"):
        self.message = message
        super().__init__(self.message)


class EmptyDraftError(Exception):
    """Exception raised when there are no registered players drafted for a PUG"""

    def __init__(self, message="There are no registered players drafted for this PUG"):
        self.message = message
        super().__init__(self.message)


class PlayerNotDraftedError(Exception):
    """Exception raised when a player isn't in the draft database"""

    def __init__(self, message="This player has not been drafted yet"):
        self.message = message
        super().__init__(self.message)


class DraftPlayer:
    def __init__(self, player, pug_id, discord_id, leader_id, team_role, draft_position):
        self.player = player
        self.pug_id = pug_id
        self.discord_id = discord_id
        self.leader_id = leader_id
        self.team_role = team_role
        self.draft_position = draft_position


class PUGEvent:
    def __init__(self, data):
        if not data or not isinstance(data, tuple):
            raise ValueError
        self.pug_id = data[0]
        self.event_id = data[1]
        self.leader_one = data[2]
        self.leader_two = data[3]
        self.team_one_role = data[4]
        self.team_two_role = data[5]
        self.teams_drafted = bool(data[6])
        self.in_progress = bool(data[7])
        self.team_one_maps_won = data[8]
        self.team_two_maps_won = data[9]
        self.total_maps_played = data[10]

    def delete(self):
        return delete_pug_event(self.pug_id)

    @classmethod
    def from_event_id(cls, event_id: int):
        data = get_pug_event_from_event_id(event_id)
        if data:
            return cls(data[0])
        else:
            raise PUGEventDoesNotExistError

    @classmethod
    def from_pug_id(cls, pug_id: int):
        data = get_pug_event_from_pug_id(pug_id)
        if data:
            return cls(data[0])
        else:
            raise PUGEventDoesNotExistError

    @classmethod
    def create(cls, event_id: int, leader_one: int, leader_two: int, team_one_role: int, team_two_role: int):
        if not pug_event_exists_event_id(event_id):
            create_pug_event(event_id, leader_one, leader_two, team_one_role, team_two_role)
            data = get_pug_event_from_event_id(event_id)
            return cls(data[0])
        else:
            raise PUGEventAlreadyExistsError

    def save_status(self):
        set_pug_event_teams_drafted(self.pug_id, self.teams_drafted)
        set_pug_event_in_progress(self.pug_id, self.in_progress)
        set_pug_event_team_one_maps_won(self.pug_id, self.team_one_maps_won)
        set_pug_event_team_two_maps_won(self.pug_id, self.team_two_maps_won)
        set_pug_event_total_maps_played(self.pug_id, self.total_maps_played)

    def draft_player(self, discord_id, leader_id, team_role, draft_position):
        player = Player.from_discord_id(discord_id)
        leader_player = Player.from_discord_id(leader_id)
        if draft_player_pug(self.pug_id, discord_id, leader_id, team_role, draft_position):
            info(f"Leader {leader_player.minecraft_username} drafted player {player.minecraft_username}")
            return True
        else:
            raise PlayerAlreadyDraftedError

    def undraft_player(self, discord_id):
        player = Player.from_discord_id(discord_id)
        if undraft_player_pug(self.pug_id, discord_id):
            info(f"Removed player {player.minecraft_username} from the draft database")
            return True
        else:
            raise PlayerNotDraftedError

    def get_drafted_players(self):
        data = get_drafted_players_pug_id(self.pug_id)
        drafted_players = []
        if data:
            for player_info in data:
                try:
                    player = Player.from_discord_id(player_info[1])
                    drafted_players.append(DraftPlayer(player, player_info[0], player_info[1], player_info[2],
                                                       player_info[3], player_info[4]))
                except PlayerDoesNotExistError:
                    info(player_info)
                    info("Player does not exist, cannot return Player object")
        if drafted_players:
            return drafted_players
        else:
            raise EmptyDraftError

