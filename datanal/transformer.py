# -*- coding: UTF-8 -*-

import os

from config.default import instance_dirpath
from datanal.tools import import_dynamically


class UnknownAdapter(Exception):
    pass


class TransformerInterface(object):
    '''Define the interface that Adapter uses
    '''

    def prepare_teams_data(self, *args, **kwargs) -> bool:
        raise NotImplementedError


    def get_teams_data(self, *args, **kwargs) -> bool:
        raise NotImplementedError


    def prepare_players_data(self, *args, **kwargs) -> bool:
        raise NotImplementedError


    def get_players_data(self, *args, **kwargs) -> bool:
        raise NotImplementedError


def get_transformer_for_api(data_src: str, game_name: str, log: bool) -> object:
    if not os.path.isfile(os.path.join(instance_dirpath, 'datanal', 'transformers', '{}.py'.format(data_src))):
        raise UnknownAdapter('Unknown transformer adapter with API name "{}"'.format(data_src))
    return import_dynamically(
        'datanal.transformers.{}'.format(data_src), 'None', 'Transformer', game_name=game_name, log=log)
