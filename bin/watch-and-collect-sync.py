#!/usr/bin/env python
# -*- coding: utf-8 -*-
# flake8: noqa: E712

import os
import sys
import requests
from requests.auth import HTTPBasicAuth

postgre_dirpath = '{}{}'.format(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'), os.sep)
sys.path.append(postgre_dirpath)

from datanal.config.api_settings import api_config


# !!! IMPORTANT !!!
# export GOOGLE_APPLICATION_CREDENTIALS="/data/app/config/gcp-developer.json"


def start_process():
    server_url_watch = 'http://127.0.0.1:80/watch-current-games'
    server_url_collect = 'http://127.0.0.1:80/collect-current-data'
    http_user = os.getenv('HTTP_USER')
    http_password = os.getenv('HTTP_PASSWORD')
    auth = HTTPBasicAuth(http_user, http_password)

    # Synchronous calls
    for data_src in api_config['data_sources']:
        for game_name in api_config['game_names']:
            requests.get('{}?data_src={}&game_name={}'.format(server_url_watch, data_src, game_name), auth=auth)
            requests.get('{}?data_src={}&game_name={}'.format(server_url_collect, data_src, game_name), auth=auth)


if __name__ == '__main__':
    start_process()
