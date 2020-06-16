# -*- coding: UTF-8 -*-

import datetime
import math

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
        self.transformer = get_transformer_for_api(self._name, self._game_name, self._log)
        super().__init__(*args, **kwargs)


    def _find_and_save_past_games(
            self, date_from: datetime.date = None, date_to: datetime.date = None, stats: dict = {}) -> dict:
        self.sql.start_trans_mode()
        cur = self.sql.cursor()
        # Find games mentioned in configuration, save them in database table `past_game_stats`
        valid_league_ids = list(toolz.itertoolz.unique([
            y[self._name]['league_id'] for x, y in api_config['{}_tournaments'.format(self._game_name)].items()
            if y[self._name] and y[self._name]['league_id']]))
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

            limit_from = None
            if date_from:
                limit_from = datetime.datetime.strptime('{} 00:00:00'.format(date_from), '%Y-%m-%d %H:%M:%S')
            limit_to = None
            if date_to:
                limit_to = datetime.datetime.strptime('{} 23:59:59'.format(date_to), '%Y-%m-%d %H:%M:%S')
            for match in matches:
                if match['league_id'] not in valid_league_ids:
                    continue
                elif ((limit_from and limit_to
                      and match['begin_at'] and match['end_at']
                      and (datetime.datetime.strptime(match['begin_at'], '%Y-%m-%dT%H:%M:%SZ') < limit_from
                           or datetime.datetime.strptime(match['end_at'], '%Y-%m-%dT%H:%M:%SZ') > limit_to))
                        or (limit_from and match['begin_at']
                            and datetime.datetime.strptime(match['begin_at'], '%Y-%m-%dT%H:%M:%SZ')
                            < limit_from)
                        or (limit_to and match['end_at']
                            and datetime.datetime.strptime(match['end_at'], '%Y-%m-%dT%H:%M:%SZ')
                            > limit_to)):
                    continue
                stats['matches_total_count'] += 1
                if not self.validator.validate_match(url_m, match, 'past_game_invalid'):
                    stats['matches_invalid_count'] += 1
                    continue

                teams = [x['opponent']['id'] for x in match['opponents']]
                for game in match['games']:
                    stats['games_total_count'] += 1
                    existing = cur.qfo('''
                        SELECT * FROM "past_game_stats" WHERE "data_src_game_id" = %(src_game_id)s
                    ''', params={'src_game_id': game['id']})
                    common_data = {
                        'data_src': self._name,
                        'game_name': self._game_name,
                        'data_src_url': url_m,
                        'data_src_game_id': game['id'],
                        'data_src_game_title': match['name'],
                        'data_src_start_datetime': match['begin_at'],
                        'data_src_finish_datetime': match['end_at'],
                        'data_src_tournament_id': match['serie_id'],
                        'data_src_tournament_title': match['serie']['full_name']
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

                    url_g = '{}/games/{}'.format(api_config[self._game_name]['provider2_slug'], game['id'])
                    headers, data = self.send_request(api_endpoint=url_g)

                    if not self.validator.validate_game(url_m, stats_game_id, data, match, 'past_game_invalid'):
                        stats['games_invalid_count'] += 1
                        continue

                    # Save team and player game stats
                    stats['datapoints_unavailable_count'] += self._save_team_stats(
                        url_g, stats_game_id, game['id'], data, teams, match['games'])
                    stats['datapoints_unavailable_count'] += self._save_player_stats(url_g, stats_game_id, data)

        # Save statistics into "past_game_analysis" table
        final_stats = self._transform_stats_and_save_analysis(self._name, stats)

        self.sql.finish_trans_mode()
        return final_stats


    def _save_team_stats(
            self, url: str, stats_game_id: int, game_id: int, data: dict, teams: list, games_data: dict) -> int:
        prepared_data = self.transformer.prepare_teams_data(teams, data, game_id, games_data)
        common_data = {
            'stats_game_id': stats_game_id,
            'data_src_url': url
        }
        teams_data = self.transformer.get_teams_data(prepared_data, data, teams)
        return self._save_team_stats_common(common_data, teams_data)


    def _round_up(self, n, decimals=0):
        multiplier = 10 ** decimals
        return math.ceil(n * multiplier) / multiplier
