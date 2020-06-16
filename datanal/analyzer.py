# -*- coding: UTF-8 -*-

import statistics
from collections import OrderedDict
from typing import NewType
from copy import deepcopy

from lib.libpool import LibPool
from datanal.config.api_settings import api_config


StrNone = NewType('StrNone', (str, None))
IntNone = NewType('IntNone', (int, None))


class Analyzer(object):

    def process_data(
            self, type: str, data_src: str, game_name: StrNone = None,
            data_src_tournament_id: IntNone = None) -> OrderedDict:
        if type == 'past':
            # There is online analysis when grabbing data , so no need for this
            raise NotImplementedError

        # Current data
        sql = LibPool().libsql
        sql.start_trans_mode()
        cur = sql.cursor()

        # Games
        # games_watch_count
        query_addon = ''
        if game_name is not None:
            query_addon = """\nAND "W"."game_name" = %(game_name)s"""
        if data_src_tournament_id is not None:
            query_addon += """\nAND "W"."data_src_tournament_id" = %(data_src_tournament_id)s"""
        games_watch_data = cur.qfo('''
            SELECT COUNT("W"."id") AS "count"
            FROM "current_game_watch" "W"
            WHERE "W"."data_src" = %(data_src)s
                AND "W"."is_deleted" = false {}
        '''.format(query_addon),
            {'data_src': data_src, 'game_name': game_name, 'data_src_tournament_id': data_src_tournament_id})
        games_watch_count = games_watch_data['count']
        if games_watch_count == 0:
            return 'No games to watch'

        # games_watch_with_stats_count
        games_watch_with_stats_data = cur.qfa('''
            SELECT "W"."id"
            FROM "current_game_watch" "W"
            INNER JOIN "current_game_stats" "S"
                ON "S"."watch_game_id" = "W"."id"
            WHERE "W"."data_src" = %(data_src)s
                AND "W"."is_deleted" = false {}
            GROUP BY "W"."id"
        '''.format(query_addon),
            {'data_src': data_src, 'game_name': game_name, 'data_src_tournament_id': data_src_tournament_id})
        games_watch_with_stats_count = len(games_watch_with_stats_data)
        if games_watch_with_stats_count == 0:
            return 'No games to watch with stats to analyze'

        # games_correction_percent
        games_watch_with_stats_percent = 0
        if games_watch_with_stats_count > 0:
            games_watch_with_stats_percent = round(games_watch_with_stats_count * 100 / games_watch_count, 2)

        # Get stats data for later analysis
        games_stats_data = cur.qfa('''
            SELECT
                "W"."id" AS "watch_id",
                "W"."game_name",
                "W"."data_src_finish_datetime",
                COUNT("S"."id") AS "stats_count",
                ARRAY_AGG ("S"."id"::int8) "stats"
            FROM "current_game_watch" "W"
            INNER JOIN "current_game_stats" "S"
                ON "S"."watch_game_id" = "W"."id"
            WHERE "W"."data_src" = %(data_src)s
                AND "W"."is_deleted" = false {}
            GROUP BY "W"."id"
            ORDER BY "W"."id"
        '''.format(query_addon),
            {'data_src': data_src, 'game_name': game_name, 'data_src_tournament_id': data_src_tournament_id})
        games_stats_watch_ids = [x['watch_id'] for x in games_stats_data]
        games_stats_counts = [x['stats_count'] for x in games_stats_data]
        games_stats_corrected_ids = [x['stats'] for x in games_stats_data if x['stats_count'] > 1]
        games_stats_corrected_first_last_ids = [(min(x['stats']), max(x['stats']))
                                                for x in games_stats_data if x['stats_count'] > 1]

        # games_watch_with_stats_corrected_count
        games_watch_with_stats_corrected_count = len(games_stats_corrected_ids)

        # games_watch_with_stats_corrected_percent
        games_watch_with_stats_corrected_percent = 0
        if games_watch_with_stats_corrected_count > 0:
            games_watch_with_stats_corrected_percent = round(
                games_watch_with_stats_corrected_count * 100 / games_watch_with_stats_count, 2)

        # games_correction_count
        correction_count_list = [x for x in games_stats_counts if x > 1]
        games_stats_correction_count = sum(correction_count_list) - len(correction_count_list)  # Minus first game

        # games_stats_correction_per_game_average_count
        games_stats_correction_per_game_average_count = 0
        if games_watch_with_stats_corrected_count > 0:
            games_stats_correction_per_game_average_count = round(
                games_stats_correction_count / games_watch_with_stats_corrected_count, 2)

        # games_stats_game_end_save_stats_average_seconds_diff
        games_stats_save_times = []
        if games_stats_watch_ids:
            for watch_game_id in games_stats_watch_ids:
                data = cur.qfo('''
                    SELECT "W"."data_src_finish_datetime", "S"."insert_datetime"
                    FROM "current_game_watch" "W"
                    INNER JOIN "current_game_stats" "S"
                        ON "S"."watch_game_id" = "W"."id"
                    WHERE "W"."id" = %s
                    ORDER BY "W"."id", "S"."id"
                    LIMIT 1
                ''', params=[watch_game_id])
                games_stats_save_times.append(
                    (data['insert_datetime'] - data['data_src_finish_datetime']).total_seconds())
        games_stats_game_end_save_stats_average_seconds_diff = 0
        if games_stats_save_times:
            games_stats_game_end_save_stats_average_seconds_diff = round(
                sum(games_stats_save_times) / len(games_stats_save_times), 2)

        # games_stats_save_stats_last_correction_average_seconds_diff
        games_stats_correction_times = []
        if games_stats_corrected_first_last_ids:
            for first_game_id, last_game_id in games_stats_corrected_first_last_ids:
                first_last = cur.qfa('''
                    SELECT "id", "insert_datetime" FROM "current_game_stats"
                    WHERE "id" IN %s
                ''', params=[(first_game_id, last_game_id)], key='id')
                games_stats_correction_times.append(
                    (first_last[last_game_id]['insert_datetime']
                     - first_last[first_game_id]['insert_datetime']).total_seconds())
        games_stats_save_stats_last_correction_average_seconds_diff = 0
        if games_stats_correction_times:
            games_stats_save_stats_last_correction_average_seconds_diff = round(
                sum(games_stats_correction_times) / len(games_stats_correction_times), 2)

        # Datapoints
        # Each team in all games has 5 players
        # datapoints_total_count
        if not game_name:
            datapoints_stats_count = (sum([5 * api_config[x['game_name']]['datapoints'] * x['stats_count']
                                      for x in games_stats_data]))
        else:
            # Total coun of saved games is `games_stats_correction_count` + `games_stats_correction_count`
            datapoints_stats_count = (5 * api_config[game_name]['datapoints']
                                      * (games_stats_correction_count + games_watch_with_stats_count))

        # datapoints_correction_count
        datapoints_stats_correction_list = []
        if games_stats_corrected_ids:
            for game_stats_ids in games_stats_corrected_ids:
                # Teams
                teams_data = cur.qfa('''
                    SELECT "TS".*, "S"."insert_datetime"
                    FROM "current_game_stats" "S"
                    INNER JOIN "current_game_team_stats" "TS"
                        ON "S"."id" = "TS"."stats_game_id"
                    WHERE "S"."id" IN %s
                    ORDER BY "TS"."data_src_team_id", "TS"."id"
                ''', [(game_stats_ids)])
                if teams_data:
                    teams_data_final = self._transform_stats_data(teams_data, 'data_src_team_id')
                    team_changes_count_per_game = self._check_stats_for_changes(teams_data_final)

                # Players
                players_data = cur.qfa('''
                    SELECT "PS".*
                    FROM "current_game_stats" "S"
                    INNER JOIN "current_game_player_stats" "PS"
                        ON "S"."id" = "PS"."stats_game_id"
                    WHERE "S"."id" IN %s
                    ORDER BY "PS"."id"
                ''', [(game_stats_ids)])
                if players_data:
                    players_data_final = self._transform_stats_data(players_data, 'data_src_player_id')
                    player_changes_count_per_game = self._check_stats_for_changes(players_data_final)

                for game_id in game_stats_ids:
                    # Changes has to be saved per stats game due max and median analyze needs
                    changes_count = 0
                    if game_id in team_changes_count_per_game:
                        changes_count += team_changes_count_per_game[game_id]
                    if game_id in player_changes_count_per_game:
                        changes_count += player_changes_count_per_game[game_id]
                    datapoints_stats_correction_list.append(changes_count)

        # assign datapoints_correction_count
        datapoints_stats_correction_count = len(datapoints_stats_correction_list)

        # datapoints_correction_percent
        datapoints_stats_correction_percent = 0
        if datapoints_stats_correction_count > 0:
            datapoints_stats_correction_percent = round(
                datapoints_stats_correction_count * 100 / datapoints_stats_count, 2)

        # datapoints_correction_max
        datapoints_stats_correction_per_game_max = 0
        if datapoints_stats_correction_list:
            datapoints_stats_correction_per_game_max = max(datapoints_stats_correction_list)

        # datapoints_correction_median
        datapoints_stats_correction_per_game_median = 0
        if datapoints_stats_correction_list:
            datapoints_stats_correction_per_game_median = statistics.median(datapoints_stats_correction_list)

        result = OrderedDict([
            ('games_watch_count', games_watch_count),
            ('games_watch_with_stats_count', games_watch_with_stats_count),
            ('games_watch_with_stats_percent', games_watch_with_stats_percent),
            ('games_watch_with_stats_corrected_count', games_watch_with_stats_corrected_count),
            ('games_watch_with_stats_corrected_percent', games_watch_with_stats_corrected_percent),
            ('games_stats_correction_count', games_stats_correction_count),
            ('games_stats_correction_per_game_average_count', games_stats_correction_per_game_average_count),
            ('games_stats_game_end_save_stats_average_minutes_diff', round(
                games_stats_game_end_save_stats_average_seconds_diff / 60, 2)),
            ('games_stats_save_stats_last_correction_average_minutes_diff', round(
                games_stats_save_stats_last_correction_average_seconds_diff / 60, 2)),
            ('datapoints_stats_count', datapoints_stats_count),
            ('datapoints_stats_correction_count', datapoints_stats_correction_count),
            ('datapoints_stats_correction_percent', datapoints_stats_correction_percent),
            ('datapoints_stats_correction_per_game_max', datapoints_stats_correction_per_game_max),
            ('datapoints_stats_correction_per_game_median', datapoints_stats_correction_per_game_median)
        ])

        # Update analysis results in database
        update_data = dict(deepcopy(result))
        for var in [('games_stats_game_end_save_stats_average_seconds_diff',
                     games_stats_game_end_save_stats_average_seconds_diff),
                    ('games_stats_save_stats_last_correction_average_seconds_diff',
                     games_stats_save_stats_last_correction_average_seconds_diff)]:
            del(update_data[var[0].replace('seconds', 'minutes')])
            update_data[var[0]] = var[1]
        cur.update('current_game_analysis', update_data, conditions={'data_src': data_src, 'game_name': game_name})

        sql.finish_trans_mode()

        # Return analysis informations
        return result


    def _check_stats_for_changes(self, data: dict) -> dict:
        changes_count_per_game = {}
        metadata_fields = ['id', 'stats_game_id', 'data_src_url', 'data_src_team_id', 'data_src_player_id']
        i = 0
        for data_id, data_stats in data.items():
            i = 0
            for data in data_stats:
                if i == 0:
                    last_data = data
                    i += 1
                    continue
                if data['stats_game_id'] not in changes_count_per_game:
                    changes_count_per_game[data['stats_game_id']] = 0
                for name, value in data.items():
                    if name in metadata_fields:
                        continue
                    if value != last_data[name]:
                        changes_count_per_game[data['stats_game_id']] += 1
                last_data = data
        return changes_count_per_game


    def _transform_stats_data(self, stats: dict, key: str) -> dict:
        data_final = {}
        for data in stats:
            if data[key] not in data_final:
                data_final[data[key]] = []
            data_final[data[key]].append(data)
        return data_final
