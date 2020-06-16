# -*- coding: UTF-8 -*-

import datetime

from lib.libpool import LibPool
from datanal.config.api_settings import api_config
from datanal.validator import ValidatorInterface


class Validator(ValidatorInterface):
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


    def validate_match(self, url: str, matches_data: dict, table: str) -> bool:
        msg = None
        if 'games' not in matches_data or not matches_data['games']:
            msg = '{} - "games" missing in data or empty'.format(self._game_name.upper())
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
        teams = [x['opponent']['id'] for x in data['match']['opponents']]
        msg = None
        if not teams or len(teams) != 2:
            msg = '{} - "opponents" empty in data or invalid for match {}'.format(
                self._game_name.upper(), match_data['id'])
        elif 'players' not in data or not data['players']:
            msg = '{} - "players" missing in data or empty for match {}'.format(
                self._game_name.upper(), match_data['id'])
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
            self._log_msg('error', msg, url=url)
            return False
        return True
