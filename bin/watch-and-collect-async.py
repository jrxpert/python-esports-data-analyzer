#!/usr/bin/env python
# -*- coding: utf-8 -*-
# flake8: noqa: E712

import os
import sys
import aiohttp
import asyncio

postgre_dirpath = '{}{}'.format(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'), os.sep)
sys.path.append(postgre_dirpath)

from datanal.config.api_settings import api_config


# !!! CANNOT BE USED BECAUSE OF REQUEST LIMIT ON PROVIDER1 API !!!
# Instead of this script use "watch-and-collect-sync.py" please.

# !!! IMPORTANT !!!
# export GOOGLE_APPLICATION_CREDENTIALS="/data/app/config/gcp-developer.json"


def start_process():
    server_url_watch = 'http://127.0.0.1:80/watch-current-games'
    server_url_collect = 'http://127.0.0.1:80/collect-current-data'
    http_user = os.getenv('HTTP_USER')
    http_password = os.getenv('HTTP_PASSWORD')
    auth = aiohttp.BasicAuth(http_user, http_password)

    # Asynchronous calls
    async def async_hit_url(url):
        connector = aiohttp.TCPConnector(limit_per_host=10)  # Parallel connections to the same endpoint
        async with aiohttp.ClientSession(connector=connector, auth=auth) as session:
            async with session.get(url) as response:
                response = await response.read()
                return response

    loop = asyncio.get_event_loop()
    tasks = []
    for data_src in api_config['data_sources']:
        for game_name in api_config['game_names']:
            task_watch = asyncio.ensure_future(
                '{}?data_src={}&game_name={}'.format(async_hit_url(server_url_watch), data_src, game_name))
            tasks.append(task_watch)
            task_collect = asyncio.ensure_future(
                '{}?data_src={}&game_name={}'.format(async_hit_url(server_url_collect), data_src, game_name))
            tasks.append(task_collect)
    loop.run_until_complete(asyncio.wait(tasks))
    # calc_data = loop.run_until_complete(asyncio.gather(*tasks))


if __name__ == '__main__':
    start_process()
