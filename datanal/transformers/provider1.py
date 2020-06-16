# -*- coding: UTF-8 -*-

from lib.libpool import LibPool
from datanal.config.api_settings import api_config
from datanal.transformer import TransformerInterface


class Transformer(TransformerInterface):
    '''Define concrete Adapter
    '''
    _name = 'provider1'
    lib_pool = LibPool()

    def __init__(self, *args, **kwargs):
        self.sql = self.lib_pool.libsql
        if 'game_name' in kwargs:
            self._game_name = kwargs['game_name']
        if 'log' in kwargs:
            self._log = kwargs['log']


    def prepare_teams_data(self, data: dict) -> dict:
        side1 = api_config[self._game_name]['provider1_sides'][0]
        side2 = api_config[self._game_name]['provider1_sides'][1]
        summary = data['match_summary']
        if self._game_name == 'csgo':
            teams = [data['match_summary'][x] for x in api_config[self._game_name]['provider1_sides']]

            # We need to pre-count round score because of using oponnents win score to set lose
            round_win = {}
            round_lose = {}
            for team_id in teams:
                round_win[team_id] = None
                round_lose[team_id] = None
            if 'scores' in summary and summary['scores']:
                for key, score in data['scores'].items():
                    round_win[key] = score
                round_lose[teams[0]] = round_win[teams[1]]
                round_lose[teams[1]] = round_win[teams[0]]

            # We need to pre-count bomb exploded / defused
            bomb_exploded = {teams[0]: None, teams[1]: None}
            bomb_defused = {teams[0]: None, teams[1]: None}
            if 'rounds' in data and data['rounds']:
                bomb_defused = {teams[0]: 0, teams[1]: 0}
                bomb_exploded = {teams[0]: 0, teams[1]: 0}
                for game_round in data['rounds']:
                    for event in game_round['bomb_events']:
                        if event['type'] == 'exploded':
                            bomb_exploded[game_round['winner_team']] += 1
                        elif event['type'] == 'defused':
                            bomb_defused[game_round['winner_team']] += 1

            return {
                'bomb_plant': bomb_exploded,
                'bomb_defuse': bomb_defused,
                'round_win': round_win,
                'round_lose': round_lose
            }

        elif self._game_name == 'dota2':
            teams = [x['team_id'] for x in data['rosters']]
            team_win = {}
            team_lose = {}
            for team_id in teams:
                team_win[team_id] = int(data['winner'] == team_id)
                team_lose[team_id] = int(data['winner'] != team_id)
            return {
                'team_win': team_win,
                'team_lose': team_lose
            }

        elif self._game_name == 'lol':
            teams = [x['team_id'] for x in data['rosters']]
            players = {
                teams[0]: [x['player_id'] for x in summary[side1]['players']],
                teams[1]: [x['player_id'] for x in summary[side2]['players']]
            }

            # We need to pre-count turrets
            turrets = {teams[0]: None, teams[1]: None}
            if ('objective_events' in summary
                    and 'towers' in summary['objective_events']
                    and summary['objective_events']['towers']):
                turrets = {teams[0]: 0, teams[1]: 0}
                for tower in summary['objective_events']['towers']:
                    if tower['killer_id'] in players[teams[0]]:
                        turrets[teams[0]] += 1
                    elif tower['killer_id'] in players[teams[1]]:
                        turrets[teams[1]] += 1

            # We need to pre-count dragons
            dragons = {teams[0]: None, teams[1]: None}
            if ('objective_events' in summary
                    and 'dragons' in summary['objective_events']
                    and summary['objective_events']['dragons']):
                dragons = {teams[0]: 0, teams[1]: 0}
                for dragon in summary['objective_events']['dragons']:
                    if dragon['killer_id'] in players[teams[0]]:
                        dragons[teams[0]] += 1
                    elif dragon['killer_id'] in players[teams[1]]:
                        dragons[teams[1]] += 1

            # We need to pre-count barons
            barons = {teams[0]: None, teams[1]: None}
            if ('objective_events' in summary
                    and 'barons' in summary['objective_events']
                    and summary['objective_events']['barons']):
                barons = {teams[0]: 0, teams[1]: 0}
                for baron in summary['objective_events']['barons']:
                    if baron['killer_id'] in players[teams[0]]:
                        barons[teams[0]] += 1
                    elif baron['killer_id'] in players[teams[1]]:
                        barons[teams[1]] += 1

            return {
                'turret': turrets,
                'dragon': dragons,
                'baron': barons
            }


    def get_teams_data(self, prepared_data: dict, data: dict) -> dict:
        side1 = api_config[self._game_name]['provider1_sides'][0]
        side2 = api_config[self._game_name]['provider1_sides'][1]
        summary = data['match_summary']
        teams_data = {}
        for side in [side1, side2]:
            if self._game_name == 'csgo':
                team_id = summary[side]
                teams_data[team_id] = {
                    'bomb_plant': prepared_data['bomb_plant'][team_id],
                    'bomb_defuse': prepared_data['bomb_defuse'][team_id],
                    'round_win': prepared_data['round_win'][team_id],
                    'round_lose': prepared_data['round_lose'][team_id]
                }

            elif self._game_name == 'dota2':
                if side == side1:
                    team_id = data['rosters'][0]['team_id']
                elif side == side2:
                    team_id = data['rosters'][1]['team_id']
                teams_data[team_id] = {
                    'team_win': prepared_data['team_win'][team_id],
                    'team_lose': prepared_data['team_lose'][team_id]
                }

            elif self._game_name == 'lol':
                if side == side1:
                    team_id = data['rosters'][0]['team_id']
                elif side == side2:
                    team_id = data['rosters'][1]['team_id']
                teams_data[team_id] = {
                    'turret': prepared_data['turret'][team_id],
                    'dragon': prepared_data['dragon'][team_id],
                    'baron': prepared_data['baron'][team_id]
                }

            teams_data[team_id]['data_src_team_id'] = team_id

        return teams_data


    def prepare_players_data(self, data: dict) -> dict:
        if self._game_name == 'dota2':
            # Prepare players id list, specially for dota2
            return {'players':
                    {
                        data['rosters'][0]['team_id']: [x['id'] for x in data['rosters'][0]['players']],
                        data['rosters'][1]['team_id']: [x['id'] for x in data['rosters'][1]['players']]
                    }}
        return {}


    def get_players_data(self, prepared_data: dict, data: dict) -> dict:
        summary = data['match_summary']
        side1 = api_config[self._game_name]['provider1_sides'][0]
        side2 = api_config[self._game_name]['provider1_sides'][1]
        players_data = {}
        for side in [side1, side2]:
            if self._game_name == 'csgo':
                for player in summary['scoreboard'][side]:
                    player_data = self._set_common_player_stats(player)
                    players_data[player_data['data_src_player_id']] = player_data

            elif self._game_name == 'dota2':
                for player in summary['player_stats']:
                    side1_players = prepared_data['players'][data['rosters'][0]['team_id']]
                    side2_players = prepared_data['players'][data['rosters'][1]['team_id']]
                    if ((side == side1 and player['player_id'] not in side1_players)
                            or (side == side2 and player['player_id'] not in side2_players)):
                        continue  # Skip players from other team

                    player_data = self._set_common_player_stats(player)
                    player_data['tower_kill'] = None
                    if 'structure_dest' in summary:
                        for dest in summary['structure_dest']:
                            if dest['structure_type'] == 'tower' and dest['killer'] == player['player_id']:
                                if player_data['tower_kill'] is None:
                                    player_data['tower_kill'] = 0
                                player_data['tower_kill'] += 1
                    player_data['roshan_kill'] = None
                    if 'roshan_events' in summary:
                        for event in summary['roshan_events']:
                            if event['type'] == 'kill' and event['killer'] == player['player_id']:
                                if player_data['roshan_kill'] is None:
                                    player_data['roshan_kill'] = 0
                                player_data['roshan_kill'] += 1
                    players_data[player_data['data_src_player_id']] = player_data

            elif self._game_name == 'lol':
                for player in summary[side]['players']:
                    player_data = self._set_common_player_stats(player)
                    player_data['creep_score'] = None
                    if 'minion_kills' in player and 'total' in player['minion_kills']:
                        player_data['creep_score'] = player['minion_kills']['total']
                    players_data[player_data['data_src_player_id']] = player_data

        return players_data


    def _set_common_player_stats(self, player: dict) -> dict:
        return {
            'data_src_player_id': player['player_id'],
            'kill': player['kills'],
            'assist': player['assists'],
            'death': player['deaths']
        }
