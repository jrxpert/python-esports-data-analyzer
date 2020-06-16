# -*- coding: UTF-8 -*-

import datetime

from lib.libpool import LibPool
from datanal.config.api_settings import api_config
from datanal.validator import ValidatorInterface


class Validator(ValidatorInterface):
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


    def _log_msg(self, type: str, msg: str, **kwargs) -> None:
        if self._log:
            api_config[self._name]['log'] = True
        if api_config[self._name]['log'] is False:
            return
        if not hasattr(self, 'logger'):
            self.logger = LibPool().logger
        logdata = {'connection_details': api_config[self._name]}
        for name, value in kwargs.items():
            logdata[name] = value
        if type == 'warning':
            self.logger.warning(msg, logdata)
        elif type == 'error':
            self.logger.error(msg, logdata)


    def validate_match(self, url: str, matches_data: dict, tournament_data: dict, table: str) -> bool:
        msg = None
        if 'matches' not in matches_data or not matches_data['matches']:
            msg = '{} - "matches" missing in data or empty'.format(self._game_name.upper())
            # Save it as invalid and log it
            insert_data = {
                'data_src_url': url,
                'insert_datetime': datetime.datetime.utcnow(),
                'problem_msg': msg
            }
            self.sql.cursor().insert(table, insert_data)
            self._log_msg('error', msg, url=url)
            return False
        return True


    def validate_game(self, url: str, parent_game_id: int, data: dict, match_data: dict, table: str) -> bool:
        side1 = api_config[self._game_name]['provider1_sides'][0]
        side2 = api_config[self._game_name]['provider1_sides'][1]
        msg = None
        if 'rosters' not in match_data or not match_data['rosters']:
            msg = '{} - "rosters" missing in data or empty for match {}'.format(
                self._game_name.upper(), match_data['id'])
        else:

            if 'match_summary' not in data or not data['match_summary']:
                msg = '{} - "match_summary" missing in data or empty'.format(self._game_name.upper())

            elif self._game_name == 'csgo':
                if side1 not in data['match_summary'] and side2 not in data['match_summary']:
                    msg = '{} - "{}" and "{}" missing in summary data'.format(self._game_name.upper(), side1, side2)
                elif side1 not in data['match_summary']:
                    msg = '{} - "{}" missing in summary data'.format(self._game_name.upper(), side1)
                elif side2 not in data['match_summary']:
                    msg = '{} - "{}" missing in summary data'.format(self._game_name.upper(), side2)
                elif (side1 not in data['match_summary']['scoreboard']
                        and side2 not in data['match_summary']['scoreboard']):
                    msg = '{} - "{}" and "{}" missing in scoreboard data'.format(self._game_name.upper(), side1, side2)
                elif side1 not in data['match_summary']['scoreboard']:
                    msg = '{} - "{}" missing in scoreboard data'.format(self._game_name.upper(), side1, side2)
                elif side2 not in data['match_summary']['scoreboard']:
                    msg = '{} - "{"} missing in scoreboard data'.format(self._game_name.upper(), side1, side2)

            elif self._game_name == 'dota2':
                if 'rosters' not in data or not data['rosters']:
                    msg = '{} - "rosters" missing in data or empty for match {}'.format(
                        self._game_name.upper(), match_data['id'])
                elif 'winner' not in data or data['winner'] is None:
                    msg = '{} - "winner" missing in summary data or empty'.format(self._game_name.upper())
                elif 'players_stats' not in data['match_summary']:
                    msg = '{} - "players_stats" missing in data[match_summary]'.format(
                        self._game_name.upper(), side1, side2)
                else:
                    if (data['match_summary'][side1] != data['rosters'][0]['id']
                            or data['match_summary'][side2] != data['rosters'][1]['id']):
                        msg = '{} - home or away team does not correspond with rosters'.format(self._game_name.upper())

            elif self._game_name == 'lol':
                if 'rosters' not in data or not data['rosters']:
                    msg = '{} - missing "rosters" in data or empty for match {}'.format(
                        self._game_name.upper(), match_data['id'])
                elif side1 not in data['match_summary'] and side2 not in data['match_summary']:
                    msg = '{} - "{}" and "{}" missing in data[match_summary]'.format(
                        self._game_name.upper(), side1, side2)
                elif side1 not in data['match_summary']:
                    msg = '{} - "{}" missing in data[match_summary]'.format(self._game_name.upper(), side1)
                elif side2 not in data['match_summary']:
                    msg = '{} - "{}" missing in data[match_summary]'.format(self._game_name.upper(), side2)
                elif 'players' not in data['match_summary'][side1] and 'players' not in data['match_summary'][side2]:
                    msg = '{} - "players" missing in data[match_summary][{}] and data[match_summary][{}]'.format(
                        self._game_name.upper(), side1, side2)
                elif 'players' not in data['match_summary'][side1]:
                    msg = '{} - "players" missing in data[match_summary][{}]'.format(self._game_name.upper(), side1)
                elif 'players' not in data['match_summary'][side2]:
                    msg = '{} - "players" missing in data[match_summary][{}]'.format(self._game_name.upper(), side2)
                else:
                    if (data['match_summary'][side1]['id'] != data['rosters'][0]['id']
                            or data['match_summary'][side2]['id'] != data['rosters'][1]['id']):
                        msg = '{} - home or away team does not correspond with rosters'.format(self._game_name.upper())

        if msg:
            # Save it as invalid and log it
            insert_data = {
                'data_src_url': url,
                'insert_datetime': datetime.datetime.utcnow(),
                'problem_msg': msg
            }
            if table == 'current_game_invalid':
                insert_data['watch_game_id'] = parent_game_id
            elif table == 'past_game_invalid':
                insert_data['stats_game_id'] = parent_game_id
            self.sql.cursor().insert(table, insert_data)
            self._log_msg('error', msg, url=url, match_id=match_data['id'])
            return False
        return True
