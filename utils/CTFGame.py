from requests import get
from re import search, split
from pandas.io.html import read_html
from pandas import DataFrame


# Stat table column names:
# name | kit_type | playtime | kills | deaths | damage_dealt | damage_received | hp_restored | sponge_launches
# fire_extinguished | players_teleported | mobs_spawned | fire_axes | flash_bombs | assassination_attempts | headshots
# best_ks | flags_recovered | flags_stolen | flags_dropped | flags_captured | time_with_flag

# Stat table kit names
# ARCHER | ASSASSIN | CHEMIST | DWARF | ELF | ENGINEER | HEAVY | MAGE | MEDIC | NECRO | NINJA | PYRO | SCOUT
# SOLDIER | FASHIONISTA


def get_server_games(server_ip):
    ctf_html = get('https://www.brawl.com/MPS/MPSStatsCTF.php').text
    table_loc = split('(<table width=\"100%\" border=\"1\">)|(</table>)', ctf_html)
    games_html = table_loc[1] + table_loc[3] + table_loc[5]
    games_table = read_html(games_html)[0]
    games = games_table.loc[games_table['ip'] == server_ip]
    return games['game_id'].to_list()


class CTFGame:
    def __init__(self, game_id):
        self.game_id = game_id
        self.stat_table = DataFrame()
        self.kit_table = DataFrame()
        self.map_name = ''
        self.mvp = ''

        game_html = get(f'https://www.brawl.com/MPS/MPSStatsCTF.php?game={self.game_id}').text
        table_loc = split('(<table width=\"100%\" border=\"1\">)|(</table>)', game_html)
        stat_table_html = table_loc[1] + table_loc[3] + table_loc[5]
        kit_table_html = table_loc[7] + table_loc[9] + table_loc[11]
        stat_table = read_html(stat_table_html)[0]
        stat_table = stat_table.drop(['players_teleported', 'mobs_spawned', 'fire_axes'], axis=1)
        self.stat_table = stat_table[stat_table['damage_dealt'] > 0]
        kit_table = read_html(kit_table_html)[0].sort_values(by=['name', 'kit_type'])
        kit_table = kit_table.drop(['players_teleported', 'mobs_spawned', 'fire_axes'], axis=1)
        self.kit_table = kit_table[kit_table['damage_dealt'] > 0]

        map_loc = search('Map: [^<]*</h1>', game_html)
        if map_loc:
            self.map_name = map_loc.group()[5:-5]
        else:
            self.map_name = ''

        mvp_loc = split('(title="u the real mvp :V">)|(</a>)', game_html)
        if len(mvp_loc) > 3:
            self.mvp = mvp_loc[3]

    def get_stats(self, stat_name, n=1):
        if not self.stat_table.empty:
            lower_stat_name = stat_name.lower()
            stats = self.stat_table.nlargest(n, lower_stat_name, 'all')  # Get largest n stats
            records = stats[['name', lower_stat_name]].to_records(index=False)  # Get IGN and stat from data frame
            list_records = list(records)  # Convert dataframe to list of tuples
            ret_val = []
            for player in list_records:
                ret_val.append((player[0], player[1]))
            return ret_val
        else:
            return []

    def get_kit_stats(self, stat_name, kit_name, n=1):
        if not self.kit_table.empty:
            lower_stat_name = stat_name.lower()
            upper_kit_name = kit_name.upper()
            kit_stats = self.kit_table.loc[self.kit_table['kit_type'] == upper_kit_name]  # Get kit_name stats
            stats = kit_stats.nlargest(n, lower_stat_name, 'all')  # Get largest n stats
            records = stats[['name', lower_stat_name]].to_records(index=False)  # Get IGN and stat from data frame
            list_records = list(records)  # Convert dataframe to list of tuples
            ret_val = []
            for player in list_records:
                ret_val.append((player[0], player[1]))
            return ret_val
        else:
            return []

    def get_player_stats(self, stat_name, player_name):
        if not self.kit_table.empty:
            lower_stat_name = stat_name.lower()
            return self.stat_table.loc[self.stat_table['name'] == player_name, ['name', lower_stat_name]].to_records(
                index=False)
        else:
            return []
