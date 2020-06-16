# -*- coding: UTF-8 -*-

import datetime
from typing import NewType

import cherrypy
import toolz

from lib.libpool import LibPool
from datanal.config.api_settings import api_config
from datanal.watcher import WatcherInterface
from datanal.tools import get_time_limit
from datanal.validator import get_validator_for_api
from datanal.transformer import get_transformer_for_api


DictNone = NewType('DictNone', (dict, None))


class Watcher(WatcherInterface):
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
        self.time_limit = int(get_time_limit())
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


    def watch_current_games(self) -> None:
        self.sql.start_trans_mode()
        cur = self.sql.cursor()
        # If there are some new just finished games mentioned in specification founded,
        # save them in database table `current_game_watch`
        valid_tournament_ids = list(toolz.itertoolz.unique([
            y[self._name]['tournament_id'] for x, y in api_config['{}_tournaments'.format(self._game_name)].items()
            if y[self._name] and y[self._name]['tournament_id']]))
        if not valid_tournament_ids:
            msg = 'No valid tournaments were found for Provider 2'
            self._log_msg('error', msg)
            return
        for tournament_id in valid_tournament_ids:
            series = {'last_page': 1}  # Fake for loop start
            series_current_page = 0
            while series['last_page'] > series_current_page:  # Pagination
                series_current_page += 1
                # NOTE: `&tiers[]=1` is not necessary, when we filter tournament ids,
                # its open to lower levels of tournaments for testing
                url_s = 'series?games[]={}&with[]=matches&is_over=true&tournaments[]={}&page={}'.format(
                    api_config[self._game_name]['provider1_id'],
                    tournament_id,
                    series_current_page)
                headers, series = self.send_request(api_endpoint=url_s)
                if not series or 'data' not in series:
                    msg = 'No data were found for Provider 2'
                    self._log_msg('error', msg, url=url_s)
                    return

                limit_datetime = datetime.datetime.utcnow() - datetime.timedelta(minutes=self.time_limit)
                for serie in series['data']:
                    if (serie['end'] is None
                            or datetime.datetime.strptime(serie['end'], '%Y-%m-%d %H:%M:%S') < limit_datetime):
                        continue

                    url_m = 'series/{}?with[]=matches'.format(serie['id'])
                    headers, matches = self.send_request(api_endpoint=url_m)
                    if not self.validator.validate_match(url_m, matches, serie, 'current_game_invalid'):
                        continue

                    for match in matches['matches']:
                        existing = cur.qfo('''
                            SELECT * FROM "current_game_watch"
                            WHERE "data_src_game_id" = %(src_game_id)s
                            AND "is_deleted" = false
                        ''', params={'src_game_id': match['id']})
                        if existing:
                            continue

                        common_data = {
                            'data_src': self._name,
                            'game_name': self._game_name,
                            'data_src_url': url_s,
                            'data_src_game_id': match['id'],
                            'data_src_game_title': matches['title'],
                            'data_src_start_datetime': matches['start'],
                            'data_src_finish_datetime': matches['end'],
                            'data_src_tournament_id': serie['tournament_id'],
                            'data_src_tournament_title': None,
                            'insert_datetime': datetime.datetime.utcnow(),
                            'is_watching': True
                        }
                        cur.insert('current_game_watch', common_data)
                        watch_game_id = cur.get_last_id('current_game_watch')

                        url_g = 'matches/{}?with[]=summary'.format(match['id'])
                        headers, data = self.send_request(api_endpoint=url_g)

                        if not self.validator.validate_game(url_g, watch_game_id, data, match, 'current_game_invalid'):
                            cur.update('current_game_watch',
                                       {'is_watching': False, 'is_deleted': True},
                                       {'id': watch_game_id})

        self.sql.finish_trans_mode()


    def collect_current_data(self) -> None:
        # Look for finished games (not longer than hour ago) mentioned in database table `current_game_watch`
        # and collect data for them into tables with team and player stats
        self.sql.start_trans_mode()
        cur = self.sql.cursor()
        matches = cur.qfa('''
            SELECT * FROM "current_game_watch"
            WHERE "is_watching" = true
            AND "is_deleted" = false
            AND "data_src" = %s
            AND "game_name" = %s
        ''', [self._name, self._game_name])

        for match in matches:
            url_m = 'matches/{}?with[]=summary'.format(match['data_src_game_id'])
            headers, data = self.send_request(api_endpoint=url_m)

            # Save game stats connection object
            stats_game_id, unchanged_game_id = self._save_game_stats_connection_objects(match['id'])

            # Need to find last stats id
            prev_stats_game_id = self._get_previous_game_id(match['id'])

            # Save team and player game stats
            changes_count = {}
            changes_count['team'] = self._save_team_stats(
                url_m, stats_game_id, prev_stats_game_id, unchanged_game_id, data)
            changes_count['player'] = self._save_player_stats(
                url_m, stats_game_id, prev_stats_game_id, unchanged_game_id, data)
            self._solve_changes_count_aftermath(changes_count, stats_game_id, unchanged_game_id)

            # Set watching false if its over limit now
            self._check_watching_limit(match['id'], match['insert_datetime'])

        self.sql.finish_trans_mode()


    def _save_team_stats(
            self, url: str, stats_game_id: int, prev_stats_game_id: int,
            unchanged_game_id: int, data: dict) -> DictNone:
        # Load last stats to have a data for comparison
        last_data = self._get_last_data(prev_stats_game_id, 'team')
        prepared_data = self.transformer.prepare_teams_data(data)
        common_data = {
            'data_src_url': url
        }
        teams_data = self.transformer.get_teams_data(prepared_data, data)
        return self._save_team_stats_common(stats_game_id, unchanged_game_id, common_data, teams_data, last_data)
