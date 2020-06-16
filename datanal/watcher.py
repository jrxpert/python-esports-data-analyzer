# -*- coding: UTF-8 -*-

import os
import datetime
from typing import NewType
import copy

import toolz

from config.default import instance_dirpath
from datanal.tools import import_dynamically
from datanal.tools import get_time_limit
from datanal.transformer import get_transformer_for_api


DictNone = NewType('DictNone', (dict, None))


class UnknownAdapter(Exception):
    pass


class WatcherInterface(object):
    '''Define the interface that Adapter uses
    '''

    def __init__(self, *args, **kwargs):
        self.transformer = get_transformer_for_api(self._name, self._game_name, self._log)
        self.time_limit = int(get_time_limit())


    def watch_current_games(self) -> None:
        raise NotImplementedError


    def collect_current_data(self) -> None:
        raise NotImplementedError


    def _solve_changes_count_aftermath(self, changes_count: dict, stats_game_id: int, unchanged_game_id: int) -> None:
        cur = self.sql.cursor()
        if changes_count['team'] is None and changes_count['player'] is None:
            # changes_count == -1 -> First stats saved
            # First stats saved can be removed, they are only in stats tables
            cur.q('''DELETE FROM "current_game_unchanged" WHERE "id" = %s''', [unchanged_game_id])
        elif sum(changes_count['team'].values()) == 0 and sum(changes_count['player'].values()) == 0:
            # Equal stats can be removed, they are only in unchanged tables
            cur.q('''DELETE FROM "current_game_stats" WHERE "id" = %s''', [stats_game_id])
        else:
            # changes_count > 0 -> Changed stats saved
            # Delete obsolete entry
            for key in ['team', 'player']:
                for data_id, count in changes_count[key].items():
                    if count == 0:
                        var = 'stats'
                    else:
                        var = 'unchanged'
                    cur.q('''
                        DELETE FROM "current_game_{key}_{var}"
                        WHERE "stats_game_id" = %s AND "data_src_{key}_id" = %s
                    '''.format(key=key, var=var), [stats_game_id, data_id])


    def _save_game_stats_connection_objects(self, watch_game_id: int) -> tuple:
        cur = self.sql.cursor()
        insert_data = {
            'watch_game_id': watch_game_id,
            'insert_datetime': datetime.datetime.utcnow()
        }
        # Insert into both tables, mostly they create whole picture of datapoints in time together
        cur.insert('current_game_stats', insert_data)
        stats_game_id = cur.get_last_id('current_game_stats')
        cur.insert('current_game_unchanged', insert_data)
        unchanged_game_id = cur.get_last_id('current_game_unchanged')
        cur.update('current_game_stats', {'unchanged_game_id': unchanged_game_id}, {'id': stats_game_id})
        cur.update('current_game_unchanged', {'stats_game_id': stats_game_id}, {'id': unchanged_game_id})
        return stats_game_id, unchanged_game_id


    def _get_previous_game_id(self, watch_game_id: int) -> int:
        cur = self.sql.cursor()
        prev_stats_game = cur.qfo('''
            SELECT "id" FROM "current_game_stats"
            WHERE "watch_game_id" = %s ORDER BY "id" DESC LIMIT 1
        ''', [watch_game_id])
        prev_stats_game_id = 0
        if prev_stats_game:
            prev_stats_game_id = prev_stats_game['id']
        return prev_stats_game_id


    def _check_watching_limit(self, watch_game_id: int, watch_insert_datetime: datetime.datetime) -> int:
        cur = self.sql.cursor()
        limit_datetime = watch_insert_datetime + datetime.timedelta(minutes=self.time_limit)
        if limit_datetime <= datetime.datetime.utcnow():
            cur.update('current_game_watch', {'is_watching': False}, {'id': watch_game_id})


    def _get_last_data(self, prev_stats_game_id: int, key: str) -> dict:
        cur = self.sql.cursor()
        return cur.qfa('''
            SELECT "DS".* FROM "current_game_stats" "S"
            INNER JOIN "current_game_{}_stats" "DS"
                ON "DS"."stats_game_id" = "S"."id"
            WHERE "S"."id" = %s
        '''.format(key), [prev_stats_game_id], key='data_src_{}_id'.format(key))


    def _save_team_stats_common(
            self, stats_game_id: int, unchanged_game_id: int,
            common_data: dict, teams_data: dict, last_data: dict) -> dict:
        cur = self.sql.cursor()
        count_changes = {}
        for team_id, team_data in teams_data.items():
            # Save team stats
            for table, stats_id_value in {'current_game_team_stats': stats_game_id,
                                          'current_game_team_unchanged': unchanged_game_id}.items():
                final_data = copy.deepcopy(common_data)
                final_data['stats_game_id'] = stats_id_value
                cur.insert(table, toolz.dicttoolz.merge(final_data, team_data))
            count_changes[team_id] = self._count_stats_changes(
                ['bomb_plant', 'bomb_defuse', 'round_win', 'round_lose',
                 'team_win', 'team_lose', 'turret', 'dragon', 'baron'],
                last_data, team_id, team_data)

        if len(last_data) == 0:
            count_changes = None  # First stats saved
        return count_changes


    def _save_player_stats(
            self, url: str, stats_game_id: int, prev_stats_game_id: int,
            unchanged_game_id: int, data: dict) -> DictNone:
        # Load last stats to have a data for comparison
        last_data = self._get_last_data(prev_stats_game_id, 'player')
        prepared_data = self.transformer.prepare_players_data(data)
        common_data = {
            'data_src_url': url
        }
        players_data = self.transformer.get_players_data(prepared_data, data)

        cur = self.sql.cursor()
        count_changes = {}
        for player_id, player_data in players_data.items():
            # Save player stats
            for table, stats_id_value in {'current_game_player_stats': stats_game_id,
                                          'current_game_player_unchanged': unchanged_game_id}.items():
                final_data = copy.deepcopy(common_data)
                final_data['stats_game_id'] = stats_id_value
                cur.insert(table, toolz.dicttoolz.merge(final_data, player_data))
            count_changes[player_id] = self._count_stats_changes(
                ['kill', 'assist', 'death', 'tower_kill', 'roshan_kill', 'creep_score'],
                last_data, player_id, player_data)

        if len(last_data) == 0:
            count_changes = None  # First stats saved
        return count_changes


    def _count_stats_changes(self, field_keys: list, last_data: dict, last_data_key: str, now_data: dict) -> int:
        count_changes = 0
        for name in field_keys:
            if (len(last_data) > 0 and name in now_data
                    and last_data[last_data_key][name] != now_data[name]):
                count_changes += 1
        return count_changes


def get_watcher_for_api(data_src: str, game_name: str, log: bool) -> object:
    if not os.path.isfile(os.path.join(instance_dirpath, 'datanal', 'watchers', '{}.py'.format(data_src))):
        raise UnknownAdapter('Unknown watcher adapter with API name "{}"'.format(data_src))
    return import_dynamically('datanal.watchers.{}'.format(data_src), 'None', 'Watcher', game_name=game_name, log=log)
