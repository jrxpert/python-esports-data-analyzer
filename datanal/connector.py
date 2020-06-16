# -*- coding: UTF-8 -*-

import os
import datetime

from config.default import instance_dirpath
from datanal.tools import import_dynamically
from datanal.watcher import get_watcher_for_api
from datanal.grabber import get_grabber_for_api


class UnknownAdapter(Exception):
    pass


class RestClientInterface(object):
    '''Define the interface that Adapter uses
    '''

    def __init__(self, *args, **kwargs):
        if 'log' in kwargs:
            self._log = kwargs['log']


    def authenticate(self) -> None:
        raise NotImplementedError


    def watch_current_games(self, game_name: str):
        return get_watcher_for_api(self._name, game_name, self._log).watch_current_games()


    def collect_current_data(self, game_name: str):
        return get_watcher_for_api(self._name, game_name, self._log).collect_current_data()


    def grab_past_data(self, game_name: str, date_from: datetime.date, date_to: datetime.date, delete_old: bool):
        return get_grabber_for_api(self._name, game_name, self._log).grab_past_data(date_from, date_to, delete_old)


    def monitor(self) -> float:
        raise NotImplementedError


def get_connector_for_api(data_src: str, log: bool) -> object:
    if not os.path.isfile(os.path.join(instance_dirpath, 'datanal', 'client', '{}.py'.format(data_src))):
        raise UnknownAdapter('Unknown client adapter with API name "{}"'.format(data_src))
    return import_dynamically(
        'datanal.client.{}'.format(data_src), None, 'RestClient', log=log)
