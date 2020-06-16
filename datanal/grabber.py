# -*- coding: UTF-8 -*-

import os
import datetime
from collections import OrderedDict

import cherrypy
import toolz

from datanal.config.api_settings import api_config
from lib.libpool import LibPool
from config.default import instance_dirpath
from datanal.tools import import_dynamically
from datanal.transformer import get_transformer_for_api


class UnknownAdapter(Exception):
    pass


class GrabberInterface(object):
    '''Define the interface that Adapter uses
    '''
    lib_pool = LibPool()

    def __init__(self, *args, **kwargs):
        self.sql = self.lib_pool.libsql
        self.send_request = cherrypy.thread_data.client_obj.send_request
        if 'data_src' in kwargs:
            self._data_src = kwargs['data_src']
        if 'game_name' in kwargs:
            self._game_name = kwargs['game_name']
        self.transformer = get_transformer_for_api(self._name, self._game_name, self._log)


    def grab_past_data(self, date_from: datetime.date, date_to: datetime.date, delete_old: bool) -> OrderedDict:
        if delete_old:
            self._delete_past_db()
        empty_stats = {
            'data_src': '',
            'game_name': '',
            'matches_total_count': 0,
            'matches_invalid_count': 0,
            'games_total_count': 0,
            'games_invalid_count': 0,
            'datapoints_wanted_count': 0,
            'datapoints_missing_count': 0,
            'datapoints_unavailable_count': 0
        }
        stats = self._find_and_save_past_games(date_from, date_to, empty_stats)
        if 'return_msg' in stats:
            return stats['return_msg']
        # Return analysis informations
        return OrderedDict([
            ('api', stats['data_src']),
            ('game', stats['game_name']),
            ('processed_matches', stats['matches_total_count']),
            ('invalid_matches', stats['matches_invalid_count']),
            ('processed_games', stats['games_total_count']),
            ('invalid_games', stats['games_invalid_count']),
            ('processed_datapoints', stats['datapoints_wanted_count']),
            ('missing_datapoints', stats['datapoints_missing_count']),
            ('unavialable_datapoints', stats['datapoints_unavailable_count'])
        ])


    def _delete_past_db(self) -> None:
        # For past data everything is in `past_game_stats` table or its subordinates,
        # so its done only with one query
        self.sql.start_trans_mode()
        cur = self.sql.cursor()
        Q = '''DELETE FROM "past_game_stats" WHERE "data_src" = %(data_src)s AND "game_name" = %(game_name)s;'''
        cur.q(Q, params={'data_src': self._data_src, 'game_name': self._game_name})
        Q = '''
            UPDATE "past_game_analysis" SET
                "matches_total_count" = 0,
                "matches_invalid_count" = 0,
                "games_total_count" = 0,
                "games_invalid_count" = 0,
                "datapoints_wanted_count" = 0,
                "datapoints_missing_count" = 0,
                "datapoints_unavailable_count" = 0,
                "analysis_update_datetime" = NULL
            WHERE "data_src" = %(data_src)s
                AND "game_name" = %(game_name)s;
        '''
        cur.q(Q, params={'data_src': self._data_src, 'game_name': self._game_name})
        self.sql.finish_trans_mode()


    def _find_and_save_past_games(self, date_from: datetime.date, date_to: datetime.date) -> dict:
        raise NotImplementedError


    def _transform_stats_and_save_analysis(self, data_src: str, stats: dict) -> dict:
        # Each team in all games has 5 players
        datapoints_wanted_count = api_config[self._game_name]['datapoints']
        stats['datapoints_wanted_count'] = 5 * datapoints_wanted_count * (
            stats['games_total_count'] - stats['games_invalid_count'])
        datapoints_missing_count = api_config[self._game_name]['{}_missing_datapoints'.format(self._name)]
        stats['datapoints_missing_count'] = 5 * datapoints_missing_count * (
            stats['games_total_count'] - stats['games_invalid_count'])
        stats['data_src'] = data_src
        stats['game_name'] = self._game_name
        stats['analysis_update_datetime'] = datetime.datetime.utcnow()
        Q = '''
            UPDATE "past_game_analysis" SET
                "matches_total_count" = "matches_total_count" + %(matches_total_count)s,
                "matches_invalid_count" = "matches_invalid_count" + %(matches_invalid_count)s,
                "games_total_count" = "games_total_count" + %(games_total_count)s,
                "games_invalid_count" = "games_invalid_count" + %(games_invalid_count)s,
                "datapoints_wanted_count" = "datapoints_wanted_count" + %(datapoints_wanted_count)s,
                "datapoints_missing_count" = "datapoints_missing_count" + %(datapoints_missing_count)s,
                "datapoints_unavailable_count" = "datapoints_unavailable_count" + %(datapoints_unavailable_count)s,
                "analysis_update_datetime" = %(analysis_update_datetime)s
            WHERE "data_src" = %(data_src)s
                AND "game_name" = %(game_name)s;
        '''
        cur = self.sql.cursor()
        cur.q(Q, stats)
        return stats


    def _save_team_stats_common(self, common_data: dict, teams_data: dict) -> int:
        cur = self.sql.cursor()
        count_missing = 0
        for team_id, team_data in teams_data.items():
            # Save team stats
            cur.insert('past_game_team_stats', toolz.dicttoolz.merge(common_data, team_data))
            count_missing += self._count_stats_missing(
                ['bomb_plant', 'bomb_defuse', 'round_win', 'round_lose',
                 'team_win', 'team_lose', 'turret', 'dragon', 'baron'],
                team_data)
        return count_missing


    def _save_player_stats(self, url: str, stats_game_id: int, data: dict) -> int:
        prepared_data = self.transformer.prepare_players_data(data)
        common_data = {
            'stats_game_id': stats_game_id,
            'data_src_url': url
        }
        players_data = self.transformer.get_players_data(prepared_data, data)

        cur = self.sql.cursor()
        count_missing = 0
        for player_id, player_data in players_data.items():
            # Save player stats
            cur.insert('past_game_player_stats', toolz.dicttoolz.merge(common_data, player_data))
            count_missing += self._count_stats_missing(
                ['kill', 'assist', 'death', 'tower_kill', 'roshan_kill', 'creep_score'],
                player_data)

        return count_missing


    def _count_stats_missing(self, field_keys: list, data: dict) -> int:
        count_missing = 0
        for name in field_keys:
            if name in data and data[name] is None:
                count_missing += 1
        return count_missing


def get_grabber_for_api(data_src: str, game_name: str, log: bool) -> object:
    if not os.path.isfile(os.path.join(instance_dirpath, 'datanal', 'grabbers', '{}.py'.format(data_src))):
        raise UnknownAdapter('Unknown grabber adapter with API name "{}"'.format(data_src))
    return import_dynamically(
        'datanal.grabbers.{}'.format(data_src), 'None', 'Grabber', data_src=data_src, game_name=game_name, log=log)
