# -*- coding: UTF-8 -*-

from importlib import import_module
import json
from decimal import Decimal
from typing import NewType
import os
import uuid
from zipfile import ZipFile
import subprocess

from lib.libpool import LibPool
from config.settings import app_config
from lib.sql.config.settings import db_config
from datanal.config.api_settings import api_config


ListDict = NewType('ListDict', (list, dict))
IntStr = NewType('IntStr', (int, str))


def import_dynamically(module_name: str, package_name: str, class_name: str, *args, **kwargs) -> object:
    """
    Returns instance of loaded class instance
    """
    module_object = import_module(module_name, package_name)
    target_class = getattr(module_object, class_name)
    return target_class(*args, **kwargs)


def default_json_encoder(o):
    if hasattr(o, 'isoformat'):
        return o.isoformat()
    elif isinstance(o, Decimal):
        return float(o)
    else:
        raise TypeError('Object of type %s with value of %s is not JSON serializable'.format(type(o), repr(o)))


def to_json(data: ListDict, indent: IntStr = None) -> str:
    out = json.dumps(data, indent=indent, ensure_ascii=False, default=default_json_encoder)
    return out


def prepare_data_output(type: str, output: str, tmp_file_path: str) -> bool:
    # Save selected data from database to tmp_file_path
    if output == 'sql':
        return save_database_dump(type, tmp_file_path)
    elif output == 'csv':
        return save_database_csv(type, tmp_file_path)


def save_database_dump(type: str, output_filepath: str) -> bool:
    sql = LibPool().libsql
    cmd = "pg_dump --file='{}' --data-only --encoding=utf8".format(output_filepath)
    cmd += ' --quote-all-identifiers --no-tablespaces --no-owner --inserts'
    cmd += " --table='{}_*'".format(type)
    cmd += ' --dbname=postgresql://{user}:{password}@{host}:{port}/{dbname}'''.format(
        **db_config['database'][sql.active_database])

    if subprocess.call(cmd, shell=True) == 0:
        # replace SET client_min_messages = warning; with "fatal" to avoid warnings
        content = None
        with open(output_filepath, 'r') as data_file:
            content = data_file.read()
        content = content.replace('client_min_messages = warning', 'client_min_messages = fatal')
        with open(output_filepath, 'w') as data_file:
            data_file.write(content)
        return True
    return False


def save_database_csv(type: str, output_filepath: str) -> True:
    tables = [
        '{}_game_analysis'.format(type)
    ]
    if type == 'current':
        tables = ['current_game_watch'] + tables
    if type == 'past':
        tables = ['past_game_stats'] + tables

    joined_tables = [
        '{}_game_player_stats'.format(type),
        '{}_game_team_stats'.format(type)
    ]
    if type == 'current':
        joined_tables = ['current_game_stats', 'current_game_unchanged',
                         'current_game_team_unchanged', 'current_game_player_unchanged'] + joined_tables

    # Save database data in CSV files
    sql = LibPool().libsql
    sql.start_trans_mode()
    cur = sql.cursor()
    tmp_files = {}
    queries = []

    for table in tables:
        csv_tmp_file_path = os.path.normpath(os.path.join(
            app_config['path_storage'], 'tmp', str(uuid.uuid4())))
        tmp_files['{}.csv'.format(table)] = csv_tmp_file_path
        queries.append('''COPY (SELECT * FROM "{}") TO '{}' WITH CSV HEADER;'''.format(
            table, csv_tmp_file_path))

    i = 0
    for table in joined_tables:
        i += 1
        csv_tmp_file_path = os.path.normpath(os.path.join(
            app_config['path_storage'], 'tmp', str(uuid.uuid4())))
        tmp_files['{}.csv'.format(table)] = csv_tmp_file_path
        if i == 1 and type == 'current':
            queries.append('''
                COPY (
                    SELECT "S".*
                    FROM "current_game_watch" "W"
                    INNER JOIN "{}" "S"
                        ON "S"."watch_game_id" = "W"."id"
                ) TO '{}' WITH CSV HEADER;'''.format(table, csv_tmp_file_path))
        elif type == 'current':
            queries.append('''
                COPY (
                    SELECT "TABLE".*
                    FROM "current_game_watch" "W"
                    INNER JOIN "current_game_stats" "S"
                        ON "S"."watch_game_id" = "W"."id"
                    INNER JOIN "{}" "TABLE"
                        ON "TABLE"."stats_game_id" = "S"."id"
                ) TO '{}' WITH CSV HEADER;'''.format(table, csv_tmp_file_path))
        elif type == 'past':
            queries.append('''
                COPY (
                    SELECT "TABLE".*
                    FROM "past_game_stats" "S"
                    INNER JOIN "{}" "TABLE"
                        ON "TABLE"."stats_game_id" = "S"."id"
                ) TO '{}' WITH CSV HEADER;'''.format(table, csv_tmp_file_path))

    for query in queries:
        cur.q(query)
    sql.finish_trans_mode()

    # ZIP files into final package
    with ZipFile(output_filepath, 'w') as myzip:
        for tmp_name, tmp_file in tmp_files.items():
            myzip.write(tmp_file, tmp_name)
            os.unlink(tmp_file)

    return True


time_limit_file_path = csv_tmp_file_path = os.path.normpath(os.path.join(
    app_config['path_storage'], 'log', 'time-limit.txt'))


def get_time_limit() -> str:
    # Return current time limit from plaintext file
    if not os.path.exists(time_limit_file_path):
        save_time_limit(api_config['watch_limit'])
    with open(time_limit_file_path, 'r') as fh:
        limit = fh.read()
    return limit


def save_time_limit(limit: int) -> True:
    # Save new time limit into plaintext file
    with open(time_limit_file_path, 'w') as fh:
        fh.write(str(limit))
    return True


tournaments_base_path = csv_tmp_file_path = os.path.normpath(os.path.join(
    app_config['path_instance'], 'datanal', 'config'))


def get_tournaments(game_name: str) -> True:
    # Return current list of tournaments to watch from JSON file
    tournaments_file_path = os.path.join(tournaments_base_path, '{}_tournaments.json'.format(game_name))
    with open(tournaments_file_path, 'r') as fh:
        tournaments = json.loads(fh.read())
    return {'game_name': game_name, 'tournaments': tournaments}


def save_tournaments(game_name: str, tournaments: dict) -> True:
    # Save new list of tournaments to watch into JSON file
    tournaments_file_path = os.path.join(tournaments_base_path, '{}_tournaments.json'.format(game_name))
    with open(tournaments_file_path, encoding='utf-8', mode='w') as fh:
        out = json.dumps(tournaments, indent=4, ensure_ascii=False, default=default_json_encoder)
        fh.write(out)
    return True
