# -*- coding: UTF-8 -*-

from lib.libpool import LibPool
from datanal.transformer import TransformerInterface


class Transformer(TransformerInterface):
    '''Define concrete Adapter
    '''
    _name = 'provider2'
    lib_pool = LibPool()

    def __init__(self, *args, **kwargs):
        self.sql = self.lib_pool.libsql
        if 'game_name' in kwargs:
            self._game_name = kwargs['game_name']
        if 'log' in kwargs:
            self._log = kwargs['log']


    def prepare_teams_data(self, teams: list, data: dict, game_id: int, games_data: dict) -> dict:
        if self._game_name == 'csgo':
            # We need to pre-count round score because of using oponnents win score to set lose
            round_win = {}
            round_lose = {}
            for team_id in teams:
                round_win[team_id] = None
                round_lose[team_id] = None
            if data['rounds_score']:
                for score in data['rounds_score']:
                    round_win[score['team_id']] = score['score']
                round_lose[teams[0]] = round_win[teams[1]]
                round_lose[teams[1]] = round_win[teams[0]]

            # We need to pre-count bomb exploded / defused
            bomb_exploded = {teams[0]: None, teams[1]: None}
            bomb_defused = {teams[0]: None, teams[1]: None}
            if data['rounds']:
                bomb_defused = {teams[0]: 0, teams[1]: 0}
                bomb_exploded = {teams[0]: 0, teams[1]: 0}
                for game_round in data['rounds']:
                    if game_round['outcome'] == 'exploded':
                        bomb_exploded[game_round['winner_team']] += 1
                    elif game_round['outcome'] == 'defused':
                        bomb_defused[game_round['winner_team']] += 1

            return {
                'bomb_plant': bomb_exploded,
                'bomb_defuse': bomb_defused,
                'round_win': round_win,
                'round_lose': round_lose
            }

        elif self._game_name == 'dota2':
            # We need to pre-find winner team
            team_win = {}
            team_lose = {}
            winner_team_id = None
            for game in games_data:
                if game['id'] == game_id:
                    winner_team_id = game['winner']['id']
                    break
            for team_id in teams:
                team_win[team_id] = int(winner_team_id == team_id)
                team_lose[team_id] = int(winner_team_id != team_id)
            return {
                'team_win': team_win,
                'team_lose': team_lose
            }

        elif self._game_name == 'lol':
            # We need to pre-find team dragon and baron kills
            turrets = {teams[0]: None, teams[1]: None}
            dragons = {teams[0]: None, teams[1]: None}
            barons = {teams[0]: None, teams[1]: None}
            for team_id in teams:
                for var in data['teams']:
                    if var['team']['id'] == team_id:
                        turrets[team_id] = var['tower_kills']
                        dragons[team_id] = var['dragon_kills']
                        barons[team_id] = var['baron_kills']
                        break

            return {
                'turret': turrets,
                'dragon': dragons,
                'baron': barons
            }


    def get_teams_data(self, prepared_data: dict, data: dict, teams: list) -> dict:
        teams_data = {}
        for team_id in teams:
            if self._game_name == 'csgo':
                teams_data[team_id] = {
                    'bomb_plant': prepared_data['bomb_plant'][team_id],
                    'bomb_defuse': prepared_data['bomb_defuse'][team_id],
                    'round_win': prepared_data['round_win'][team_id],
                    'round_lose': prepared_data['round_lose'][team_id]
                }

            elif self._game_name == 'dota2':
                teams_data[team_id] = {
                    'team_win': prepared_data['team_win'][team_id],
                    'team_lose': prepared_data['team_lose'][team_id]
                }

            elif self._game_name == 'lol':
                teams_data[team_id] = {
                    'turret': prepared_data['turret'][team_id],
                    'dragon': prepared_data['dragon'][team_id],
                    'baron': prepared_data['baron'][team_id]
                }

            teams_data[team_id]['data_src_team_id'] = team_id

        return teams_data


    def prepare_players_data(self, data: dict) -> dict:
        return {}


    def get_players_data(self, prepared_data: dict, data: dict) -> dict:
        players_data = {}
        for player in data['players']:
            player_data = {
                'data_src_player_id': player['player']['id'],
                'kill': player['kills'],
                'assist': player['assists'],
                'death': player['deaths']
            }
            if self._game_name == 'dota2':
                player_data['tower_kill'] = player['tower_kills']
                player_data['roshan_kill'] = player['neutral_creep']
            elif self._game_name == 'lol':
                player_data['creep_score'] = None
                if 'kill_counters' in player and 'neutral_minions' in player['kill_counters']:
                    player_data['creep_score'] = player['kill_counters']['neutral_minions']
            players_data[player_data['data_src_player_id']] = player_data

        return players_data
