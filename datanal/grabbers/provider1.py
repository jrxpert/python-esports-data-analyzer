# -*- coding: UTF-8 -*-

import datetime

import cherrypy
import toolz

from datanal.config.api_settings import api_config
from lib.libpool import LibPool
from datanal.grabber import GrabberInterface
from datanal.validator import get_validator_for_api
from datanal.transformer import get_transformer_for_api


class Grabber(GrabberInterface):
    '''Define concrete Adapter
    '''
    _name = 'provider1'
    lib_pool = LibPool()

    def __init__(self, *args, **kwargs):
        self.sql = self.lib_pool.libsql
        self.send_request = cherrypy.thread_data.client_obj.send_request
        if 'game_name' in kwargs:
            self._game_name = kwargs['game_name']
        if 'log' in kwargs:
            self._log = kwargs['log']
        self.validator = get_validator_for_api(self._name, self._game_name, self._log)
        self.transformer = get_transformer_for_api(self._name, self._game_name, self._log)
        super().__init__(*args, **kwargs)


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


    def _find_and_save_past_games(
            self, date_from: datetime.date = None, date_to: datetime.date = None, stats: dict = {}) -> dict:
        self.sql.start_trans_mode()
        cur = self.sql.cursor()
        # Find games mentioned in configuration, save them in database table `past_game_stats`
        valid_tournament_ids = list(toolz.itertoolz.unique([
            y[self._name]['tournament_id'] for x, y in api_config['{}_tournaments'.format(self._game_name)].items()
            if y[self._name] and y[self._name]['tournament_id']]))
        series = {'last_page': 1}  # Fake for loop start
        series_current_page = 0
        while series['last_page'] > series_current_page:  # Pagination
            series_current_page += 1
            # NOTE: `&tiers[]=1` is not necessary, when we filter tournament ids,
            # its open to lower levels of tournaments for testing
            # NOTE: &tournaments[]=123,345 does not work as expected, should be only one ID -> DO NOT USE IT!!!
            url_s = 'series?games[]={}&with[]=matches&page={}'.format(
                api_config[self._game_name]['provider1_id'],
                series_current_page)
            headers, series = self.send_request(api_endpoint=url_s)
            if not series or 'data' not in series:
                return {'return_msg': 'No data were found for Provider 2.'}

            limit_from = None
            if date_from:
                limit_from = datetime.datetime.strptime('{} 00:00:00'.format(date_from), '%Y-%m-%d %H:%M:%S')
            limit_to = None
            if date_to:
                limit_to = datetime.datetime.strptime('{} 23:59:59'.format(date_to), '%Y-%m-%d %H:%M:%S')
            for serie in series['data']:
                if serie['tournament_id'] not in valid_tournament_ids:
                    continue
                elif ((limit_from and limit_to
                        and serie['start'] and serie['end']
                        and (datetime.datetime.strptime(serie['start'], '%Y-%m-%d %H:%M:%S') < limit_from
                             or datetime.datetime.strptime(serie['end'], '%Y-%m-%d %H:%M:%S') > limit_to))
                        or (limit_from and serie['start']
                            and datetime.datetime.strptime(serie['start'], '%Y-%m-%d %H:%M:%S')
                            < limit_from)
                        or (limit_to and serie['end']
                            and datetime.datetime.strptime(serie['end'], '%Y-%m-%d %H:%M:%S')
                            > limit_to)):
                    continue

                stats['matches_total_count'] += 1
                url_m = 'series/{}?with[]=matches'.format(serie['id'])
                headers, matches = self.send_request(api_endpoint=url_m)
                if not self.validator.validate_match(url_m, matches, serie, 'past_game_invalid'):
                    stats['matches_invalid_count'] += 1
                    continue

                for match in matches['matches']:
                    stats['games_total_count'] += 1
                    existing = cur.qfo('''
                        SELECT * FROM "past_game_stats" WHERE "data_src_game_id" = %(src_game_id)s
                    ''', params={'src_game_id': match['id']})
                    common_data = {
                        'data_src': self._name,
                        'game_name': self._game_name,
                        'data_src_url': url_s,
                        'data_src_game_id': match['id'],
                        'data_src_game_title': serie['title'],
                        'data_src_start_datetime': matches['start'],
                        'data_src_finish_datetime': matches['end'],
                        'data_src_tournament_id': serie['tournament_id'],
                        'data_src_tournament_title': None
                    }
                    if not existing:
                        common_data['insert_datetime'] = datetime.datetime.utcnow()
                        cur.insert('past_game_stats', common_data)
                        stats_game_id = cur.get_last_id('past_game_stats')
                    else:
                        stats_game_id = existing['id']
                        del(existing['id'], existing['insert_datetime'], existing['update_datetime'])
                        diff_data = dict(toolz.itertoolz.diff(common_data, existing))
                        if diff_data:
                            common_data['update_datetime'] = datetime.datetime.utcnow()
                            cur.update('past_game_stats', diff_data, conditions={'data_src_game_id': match['id']})

                    url_g = 'matches/{}?with[]=summary'.format(match['id'])
                    headers, data = self.send_request(api_endpoint=url_g)

                    if not self.validator.validate_game(url_g, stats_game_id, data, match, 'past_game_invalid'):
                        print(url_g)
                        stats['games_invalid_count'] += 1
                        continue

                    # Save team and player game stats
                    stats['datapoints_missing_count'] += self._save_team_stats(url_m, stats_game_id, data)
                    stats['datapoints_missing_count'] += self._save_player_stats(url_m, stats_game_id, data)

        # Save statistics into "past_game_analysis" table
        final_stats = self._transform_stats_and_save_analysis(self._name, stats)

        self.sql.finish_trans_mode()
        return final_stats


    def _save_team_stats(
            self, url: str, stats_game_id: int, data: dict) -> int:
        prepared_data = self.transformer.prepare_teams_data(data)
        common_data = {
            'stats_game_id': stats_game_id,
            'data_src_url': url
        }
        teams_data = self.transformer.get_teams_data(prepared_data, data)
        return self._save_team_stats_common(common_data, teams_data)
