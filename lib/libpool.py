# -*- coding: UTF-8 -*-

from lib.sql.postgre import Sql
from lib.log import setup_logger


class LibPool(object):
    sql = Sql()
    _logger = setup_logger()

    @property
    def libsql(self):
        if hasattr(self, 'sql'):
            return getattr(self, 'sql')
        raise RuntimeError('Specified library "libsql" instance does not exists')


    @property
    def logger(self) -> object:
        if hasattr(self, '_logger'):
            return getattr(self, '_logger')
        raise RuntimeError('Specified library "logger" instance does not exists')
