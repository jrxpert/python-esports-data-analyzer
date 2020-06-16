# -*- coding: UTF-8 -*-

import datetime
from typing import NewType
import math

import cherrypy
import toolz

from lib.libpool import LibPool
from datanal.config.api_settings import api_config
from datanal.watcher import WatcherInterface
from datanal.tools import get_time_limit
from datanal.validator import get_validator_for_api


DictNone = NewType('DictNone', (dict, None))


class Watcher(WatcherInterface):
    '''Define concrete Adapter
    '''
    _name = 'provider2'
    lib_pool = LibPool()

    def __init__(self, *args, **kwargs):
        self.sql = self.lib_pool.libsql
        self.send_request = cherrypy.thread_data.client_obj.send_request
        if 'game_name' in kwargs:
            self._game_name = kwargs['game_name']
        if 'log' in kwargs:
            self._log = kwargs['log']
        self.validator = get_validator_for_api(self._name, self._game_name, self._log)
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
        valid_league_ids = list(toolz.itertoolz.unique([
            y[self._name]['league_id'] for x, y in api_config['{}_tournaments'.format(self._game_name)].items()
            if y[self._name] and y[self._name]['league_id']]))
        if not valid_league_ids:
            msg = 'No valid leagues were found for Provider 1'
            self._log_msg('error', msg)
            return
        matches_last_page = 1  # Fake for loop start
        matches_current_page = 0
        while matches_last_page > matches_current_page:  # Pagination
            matches_current_page += 1
            url_m = '{}/matches/past?filter[status]=finished&league_id={}&page[size]=100&page[number]={}'.format(
                api_config[self._game_name]['provider2_slug'],
                str(valid_league_ids),
                matches_current_page)
            matches_headers, matches = self.send_request(api_endpoint=url_m)
            matches_last_page = self._round_up(int(matches_headers['X-Total']) / int(matches_headers['X-Per-Page']))
            if not matches:
                return {'return_msg': 'No data were found for Provider 1.'}
                msg = 'No data were found for Provider 1'
                self._log_msg('error', msg, url=url_m)
                return

            limit_datetime = datetime.datetime.utcnow() - datetime.timedelta(minutes=self.time_limit)
            for match in matches:
                if match['league_id'] not in valid_league_ids:
                    continue
                elif (match['end_at'] is None
                        or datetime.datetime.strptime(match['end_at'], '%Y-%m-%dT%H:%M:%SZ') < limit_datetime):
                    continue
                if not self.validator.validate_match(url_m, match, 'current_game_invalid'):
                    continue

                for game in match['games']:
                    existing = cur.qfo('''
                        SELECT * FROM "current_game_watch"
                        WHERE "data_src_game_id" = %(src_game_id)s
                        AND "is_deleted" = false
                    ''', params={'src_game_id': game['id']})
                    if existing:
                        continue

                    common_data = {
                        'data_src': self._name,
                        'game_name': self._game_name,
                        'data_src_url': url_m,
                        'data_src_game_id': game['id'],
                        'data_src_game_title': match['name'],
                        'data_src_start_datetime': match['begin_at'],
                        'data_src_finish_datetime': match['end_at'],
                        'data_src_tournament_id': match['serie_id'],
                        'data_src_tournament_title': match['serie']['full_name'],
                        'insert_datetime': datetime.datetime.utcnow(),
                        'is_watching': True
                    }
                    cur.insert('current_game_watch', common_data)
                    watch_game_id = cur.get_last_id('current_game_watch')

                    url_g = '{}/games/{}'.format(api_config[self._game_name]['provider2_slug'], game['id'])
                    headers, data = self.send_request(api_endpoint=url_g)

                    if not self.validator.validate_game(url_m, watch_game_id, data, match, 'current_game_invalid'):
                        cur.update('current_game_watch',
                                   {'is_watching': False, 'is_deleted': True},
                                   {'id': watch_game_id})

        self.sql.finish_trans_mode()


    def collect_current_data(self):
        # Look for finished games (not longer than hour ago) mentioned in database table `current_game_watch`
        # and collect data for them into tables with team and player stats
        self.sql.start_trans_mode()
        cur = self.sql.cursor()
        games = cur.qfa('''
            SELECT * FROM "current_game_watch"
            WHERE "is_watching" = true
            AND "is_deleted" = false
            AND "data_src" = %s
            AND "game_name" = %s
        ''', [self._name, self._game_name])

        for game in games:
            url_g = '{}/games/{}'.format(api_config[self._game_name]['provider2_slug'], game['data_src_game_id'])
            headers, data = self.send_request(api_endpoint=url_g)

            # Save game stats connection object
            stats_game_id, unchanged_game_id = self._save_game_stats_connection_objects(game['id'])

            # Need to find last stats id
            prev_stats_game_id = self._get_previous_game_id(game['id'])

            # Save team and player game stats
            changes_count = {}
            changes_count['team'] = self._save_team_stats(
                url_g, stats_game_id, prev_stats_game_id, unchanged_game_id,
                game['data_src_game_id'], data, data['match']['games'])
            changes_count['player'] = self._save_player_stats(
                url_g, stats_game_id, prev_stats_game_id, unchanged_game_id, data)
            self._solve_changes_count_aftermath(changes_count, stats_game_id, unchanged_game_id)

            # Set watching false if its over limit now
            self._check_watching_limit(game['id'], game['insert_datetime'])

        self.sql.finish_trans_mode()


    def _save_team_stats(
            self, url: str, stats_game_id: int, prev_stats_game_id: int,
            unchanged_game_id: int, game_id: int, data: dict, games_data: dict) -> DictNone:
        # Load last stats to have a data for comparison
        last_data = self._get_last_data(prev_stats_game_id, 'team')
        teams = [x['opponent']['id'] for x in data['match']['opponents']]
        prepared_data = self.transformer.prepare_teams_data(teams, data, game_id, games_data)
        common_data = {
            'data_src_url': url
        }
        teams_data = self.transformer.get_teams_data(prepared_data, data, teams)
        return self._save_team_stats_common(stats_game_id, unchanged_game_id, common_data, teams_data, last_data)


    def _round_up(self, n, decimals=0):
        multiplier = 10 ** decimals
        return math.ceil(n * multiplier) / multiplier
