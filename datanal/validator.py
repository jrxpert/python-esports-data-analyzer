# -*- coding: UTF-8 -*-

import os

from config.default import instance_dirpath
from datanal.tools import import_dynamically


class UnknownAdapter(Exception):
    pass


class ValidatorInterface(object):
    '''Define the interface that Adapter uses
    '''

    def validate_match(self, *args, **kwargs) -> bool:
        raise NotImplementedError


    def validate_game(self, *args, **kwargs) -> bool:
        raise NotImplementedError


def get_validator_for_api(data_src: str, game_name: str, log: bool) -> object:
    if not os.path.isfile(os.path.join(instance_dirpath, 'datanal', 'validators', '{}.py'.format(data_src))):
        raise UnknownAdapter('Unknown validator adapter with API name "{}"'.format(data_src))
    return import_dynamically(
        'datanal.validators.{}'.format(data_src), 'None', 'Validator', game_name=game_name, log=log)
