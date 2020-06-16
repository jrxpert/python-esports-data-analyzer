# -*- coding: UTF-8 -*-

import os
import json


api_config = {
    'data_sources': ['provider1', 'provider2'],
    'game_names': ['csgo', 'dota2', 'lol'],
    'watch_limit': 20,  # minutes
    'provider1': {
        'url': os.getenv('PROVIDER1_URL', 'http://some-url.com'),
        'client_id': os.getenv('PROVIDER1_CLIENT_ID', '12345'),
        'client_secret': os.getenv('PROVIDER1_CLIENT_SECRET', 'abc123'),
        'log': os.getenv('PROVIDER1_LOG', True),
        'requests_per_second': float(os.getenv('PROVIDER1_REQUESTS_PER_SECOND', 1))
    },
    'provider2': {
        'url': os.getenv('PROVIDER2_URL', 'http://some-url.com'),
        'auth_token': os.getenv('PROVIDER2_AUTH_TOKEN', '12345'),
        'log': os.getenv('PROVIDER2_LOG', True),
        'requests_per_second': float(os.getenv('PROVIDER2_REQUESTS_PER_SECOND', 2.5))
    }
}


base_path = os.path.dirname(os.path.abspath(__file__))
for game_name in api_config['game_names']:
    api_config[game_name] = {}
    conf_path = (game_name, os.path.join(base_path, '{}.json'.format(game_name)))
    tournaments_path = (
        '{}_tournaments'.format(game_name), os.path.join(base_path, '{}_tournaments.json'.format(game_name)))
    for file_path in [conf_path, tournaments_path]:
        with open(file_path[1]) as fh:
            try:
                api_config[file_path[0]] = json.load(fh)
            except ValueError:
                raise RuntimeError('Invalid JSON file "{}"'.format(file_path[1]))
