# -*- coding: UTF-8 -*-
# flake8: noqa: E303, W503

__author__ = "Jan Rieger (jrxp3r7@gmail.com)"
__copyright__ = "Copyright (c) 2019"
__version__ = "0.3.0"

'''Sql library object has to be used all over the application as SINGLETON!
It`s possible to use more instances, but then is ThreadConnectionPool useless.'''

import os
import re
from collections import OrderedDict
import threading
from typing import NewType
import time
import sys
import logging
import re

import psycopg2
import psycopg2.extensions
import psycopg2.extras
import psycopg2.pool
from psycopg2 import DatabaseError
import cherrypy

postgre_dirpath = '{}{}'.format(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'), os.sep)
sys.path.append(postgre_dirpath)

from lib import tools
from lib.sql.config.settings import db_config


Sequence = NewType('Sequence', (tuple, list, dict))
ListDict = NewType('ListDict', (list, dict))
TupleList = NewType('TupleList', (tuple, list))
IntNone = NewType('IntNone', (int, None))


class ConnectionDoesNotExist(DatabaseError):
    pass


class TransactionDoesNotExist(DatabaseError):
    pass


class Sql(object):
    thread_pool = None  # Thread connections pool

    def __init__(self, params: dict = {}) -> None:
        # Get application logger
        self.logger = logging.getLogger()  # Default Python logger
        if os.path.exists(os.path.normpath(os.path.join(
                os.path.dirname(os.path.abspath(__file__)), '..', '..', 'config', 'settings.py'))):
            # Custom loggers
            from config.settings import app_config
            if app_config['app_log_factory'] == 'file':
                self.logger = logging.getLogger('app')

        self.active_database = None

        # Select database to use
        if params and 'db' in params and params['db'] in db_config['database']:
            self.active_database = params['db']
        elif 'default' in db_config and db_config['default'] in db_config['database']:
            self.active_database = db_config['default']
        elif not self.active_database:
            raise Exception('Invalid database specification')
        self.conf = db_config['database'][self.active_database]

        self.log = False
        if ((params and 'log' in params and params['log'] is True)
                or bool(self.conf['log']) is True):
            self.log = True

        if not params or 'connect' not in params or params['connect'] is True:
            self.connect()


    def __del__(self) -> None:
        if hasattr(self, 'thread_pool') and self.thread_pool:
            self.thread_pool.closeall()  # Threading
        if hasattr(cherrypy.thread_data, 'dbconn'):
            del(cherrypy.thread_data.dbconn)


    def set_thread_pool(self) -> None:
        self.thread_pool = psycopg2.pool.ThreadedConnectionPool(
            2,  # minimum PostgreSQL database connection
            # maximum PostgreSQL database connection, should be equal to uWSGI processes * threads
            self.conf.get('maxconn', 20),
            host=self.conf['host'],
            database=self.conf['dbname'],
            user=self.conf['user'],
            password=self.conf['password'],
            port=self.conf['port'])


    def connect(self) -> psycopg2.extensions.connection:
        if hasattr(cherrypy.thread_data, 'dbconn'):
            # Connection exists, return it
            return cherrypy.thread_data.dbconn
        else:
            # Get connection from pool
            if self.thread_pool is None:
                self.set_thread_pool()
            conn = self.thread_pool.getconn(key=str(threading.get_ident()))
        cherrypy.thread_data.dbconn = conn

        # Default transaction mode is autocommit
        self.set_default_autocommit()

        # Set server version
        result = re.match(r'(?P<major>\d{1,2})0?(?P<minor>\d{1,2})0?(?P<patch>\d{1,2})', str(conn.server_version))
        self.version = float(('{}.{}').format(result.group('major'), result.group('minor')))

        return conn


    def get_conn(self) -> psycopg2.extensions.connection:
        if hasattr(cherrypy.thread_data, 'dbconn'):
            return cherrypy.thread_data.dbconn
        else:
            return self.connect()


    def disconnect(self) -> None:
        if hasattr(cherrypy.thread_data, 'dbconn'):
            # Threading connection
            conn = cherrypy.thread_data.dbconn
            if conn.autocommit is True:  # Only non transaction mode
                self.thread_pool.putconn(conn, key=str(threading.get_ident()))
        del(cherrypy.thread_data.dbconn)


    def cursor(self) -> object:
        # Method create a Cursor object that operates in the context of Connection.
        # Returns created Cursor object.
        return SqlCursor(self)


    def set_default_autocommit(self) -> None:
        conn = self.get_conn()
        conn.autocommit = True
        conn.set_session(isolation_level='READ COMMITTED')


    def start_trans_mode(self) -> None:
        conn = self.get_conn()
        conn.autocommit = False
        conn.set_session(isolation_level='READ COMMITTED')


    def finish_trans_mode(self, action: str = 'commit') -> None:
        if action not in ['commit', 'rollback']:
            raise ValueError('Transaction can be finished with actions commit or rollback only.')
        if (not hasattr(cherrypy.thread_data, 'dbconn')
                or not isinstance(getattr(cherrypy.thread_data, 'dbconn'), psycopg2.extensions.connection)):
            raise ConnectionDoesNotExist('Cannot finish a transaction. Application is not connected to a database.')
        conn = cherrypy.thread_data.dbconn
        if conn.autocommit is not False:
            raise TransactionDoesNotExist('Cannot finish a transaction. Transaction was not started.')

        if action == 'commit':
            conn.commit()
        elif action == 'rollback':
            conn.rollback()
        self.set_default_autocommit()


    def esc_name(self, var):
        """ Method escape names of columns, tables, etc.

        Args:
            var (Mixed[dict,list,tuple,str]): Variable to escape, should be dictionary or string.

        Returns:
            Escaped name.

        """
        if isinstance(var, dict):
            for key, value in var.items():
                if isinstance(value, dict):
                    var[key] = self.esc_name(value)
                else:
                    var[key] = ('"{}"').format(value)
        elif isinstance(var, list) or isinstance(var, tuple):
            var2 = var
            var = []
            for value in var2:
                if isinstance(value, list) or isinstance(var, tuple):
                    var.append(self.esc_name(value))
                else:
                    var.append(('"{}"').format(value))
        elif isinstance(var, str):
            var = ('"{}"').format(var)
        return var


    def esc_value(self, var):
        """ Method escape values which will be inserted into database.

        Args:
            var (Mixed[dict,list,tuple,str]): Variable to escape, should be dictionary or string.

        Returns:
            Escaped variable.

        """
        if isinstance(var, dict):
            for key, value in var.items():
                if isinstance(value, dict):
                    var[key] = self.esc_value(value)
                else:
                    var[key] = value.replace("'", "''")
        elif isinstance(var, list) or isinstance(var, tuple):
            var2 = var
            var = []
            for value in var2:
                if isinstance(value, list) or isinstance(var, tuple):
                    var.append(self.esc_value(value))
                else:
                    var.append(value.replace("'", "''"))
        elif isinstance(var, str):
            var = var.replace("'", "''")
        return var


    def esc_bytea(self, var: str) -> str:
        """ Method escape bytea values for database.

        Args:
            var (str): Variable to escape, should be string.

        Returns:
            Escaped binary.

        """
        if not isinstance(var, str) or var == '':
            return False
        return str.encode(var)


    def unesc_bytea(self, var: str) -> str:
        """ Method unescape bytea columns from database.

        Args:
            var (binary): Variable to unescape, should be binary.

        Returns:
            Unescaped string.

        """
        if not isinstance(var, bytes) or var == '':
            return False
        return var.decode('utf-8')



class SqlCursor(object):
    ''' Wrapper around psycopg2 cursor class '''

    def __init__(self, sql) -> None:
        self.sql = sql
        self.conn = self.sql.connect()
        self.conn_id = self.conn.get_backend_pid()

        self.affected_rows = None
        self.cursor = _PgCursor(self.conn)


    def __del__(self) -> None:
        self.close()


    def close(self) -> None:
        self.cursor.close()


    def get(self) -> psycopg2.extras.RealDictCursor:
        return self.cursor


    def _q(self, query: str, params: Sequence = None) -> bool:
        if self.sql.log is True:
            logdata = {
                'request_id': cherrypy.request.unique_id,
                'process_id': os.getpid(),
                'thread_id': threading.get_ident(),
                'connection_id': self.conn_id,
                'cursor_id': id(self)
            }
            if params:
                logdata['params'] = params

        try:
            start_time = time.perf_counter()
            self.affected_rows = self.cursor.q(query, params)
            exec_time = time.perf_counter() - start_time
            if self.sql.log is True:
                logdata['exec_time'] = exec_time
                # Evil hack to prevent logging formatter %s replacements in sql queries, etc.
                pattern = re.compile(r'''%\(?(?P<key>[^\) ]+)?\)?s''', re.M)
                log_query = pattern.sub(r'''$\g<key>''', query)
                self.sql.logger.info(log_query, logdata)
        except (psycopg2.InternalError, psycopg2.ProgrammingError, psycopg2.IntegrityError):
            self.conn.rollback()
            raise
        except (psycopg2.InterfaceError, psycopg2.OperationalError):
            if self.conn.autocommit is False:
                # This is transaction mode, which cannot be safely recovered
                raise
            else:
                # Reconnect
                self.sql.connect()
                self.cursor = _PgCursor(self.conn)
                self.affected_rows = self.cursor.q(query, params)
        else:
            return True


    def q(self, query: str, params: Sequence = None) -> bool:
        query = query.strip()
        if isinstance(params, (list, tuple)):
            for index, item in enumerate(params):
                if isinstance(item, list):
                    # List has to be converted to tuple so psycopg2 uses it as (1, 2, 3) not ARRAY [1, 2, 3]
                    params[index] = tuple(item)
        return self._q(query, params)


    def fo(self) -> dict:
        return self.cursor.fo()


    def fa(self, key: str = None) -> ListDict:
        return self.cursor.fa(key)


    def qfo(self, query: str, params: Sequence = None) -> dict:
        self.q(query, params)
        return self.fo()


    def qfa(self, query: str, params: Sequence = None, key: str = None) -> ListDict:
        self.q(query, params)
        res = self.fa(key)
        return res


    def _prepare_insert(self, table: str, data_keys: list) -> str:
        field_names = []
        placeholders = []
        for field in data_keys:
            field_names.append(self.sql.esc_name(field))
            placeholders.append('%s')
        query = ('''
            INSERT INTO {} ({}) VALUES ({})''').format(
            self.sql.esc_name(table), ', '.join(field_names), ', '.join(placeholders))
        return query


    def _prepare_update(self, table: str, data_keys: list, conditions_keys: list) -> str:
        query_sets = []
        query_conditions = []
        for field in data_keys:
            query_sets.append(('{}={}').format(self.sql.esc_name(field), '%s'))
        for field in conditions_keys:
            query_conditions.append(('{}={}').format(self.sql.esc_name(field), '%s'))
        query = ('''
            UPDATE {} SET {} WHERE {}'''.format(
            self.sql.esc_name(table), ', '.join(query_sets), ' AND '.join(query_conditions)))
        return query


    def insert(self, table: str, data: dict) -> bool:
        field_types = self.get_table_field_types(table)
        for key, value in field_types.items():
            if value == 17:
                data[key] = bytearray(data[key])  # Escape bytea value
        data_keys = list(data.keys())
        params = list(data.values())
        query = self._prepare_insert(table, data_keys)
        return self.q(query, params)


    def update(self, table: str, data: dict, conditions: dict) -> bool:
        field_types = self.get_table_field_types(table)
        for key, value in field_types.items():
            if value == 17:
                data[key] = bytearray(data[key])  # Escape bytea value
        data_keys = list(data.keys())
        conditions_keys = list(conditions.keys())
        params = list(data.values())
        params.extend(list(conditions.values()))
        query = self._prepare_update(table, data_keys, conditions_keys)
        return self.q(query, params)


    def rows(self) -> IntNone:
        if self.affected_rows == -1:
            return None
        return self.affected_rows


    def gen_id(self, generator: str) -> int:
        if not generator or not isinstance(generator, str):
            raise ValueError
        return self.cursor.gen_id(generator)


    def get_last_id(self, generator: str) -> int:
        if not generator or not isinstance(generator, str):
            raise ValueError
        return self.cursor.get_last_id(generator)


    def set_gen_id(self, generator: str, value: int) -> bool:
        if self.cursor.set_gen_id(generator, value) == 1:
            # Count of affected rows
            return True
        return False


    def get_table_fields(self, table: str) -> list:
        return self.cursor.get_table_fields(table)


    def get_table_field_types(self, table: str) -> dict:
        return self.cursor.get_table_field_types(table)



class _PgCursor(psycopg2.extras.RealDictCursor):
    # Extended psycopg2 cursor class

    def get_column_info(self) -> dict:
        # Return table columns dictionary
        self._columns = {}
        for col in self.description:
            self._columns[col[0]] = {
                'type': col[1]
            }
        return self._columns


    def q(self, query: str, params: dict = None) -> IntNone:
        # Execute query
        super().execute(query, params)
        if isinstance(super().rowcount, int):
            return super().rowcount
        tools.check_request_timeout()  # Application hook to return 408 if time is over
        return None


    def fo(self) -> dict:
        # Fetch one
        data = super().fetchone()
        table_keys = self.get_column_info().keys()
        table_infos = self.get_column_info()
        for field in table_keys:
            if table_infos[field]['type'] == 17:
                try:
                    data[field] = data[field].tobytes().decode('utf-8')  # Unescape bytea value
                except TypeError:
                    # TODO: Do not know why it raise TypeError exception, it works, but its strange
                    pass
        tools.check_request_timeout()  # Application hook to return 408 if time is over
        return data


    def fa(self, key: str = None, original: bool = False) -> ListDict:
        if original is True and key is None:
            # Fetch all as original cursor
            data = super().fetchall()
            table_keys = self.get_column_info().keys()
            table_infos = self.get_column_info()
            for field in table_keys:
                if table_infos[field]['type'] == 17:
                    for key, value in data:
                        try:
                            data[key][field] = data[key][field].tobytes().decode('utf-8')  # Unescape bytea value
                        except TypeError:
                            # TODO: Do not know why it raise TypeError exception, it works, but its strange
                            pass
        else:
            if key is None or key not in self.get_column_info().keys():
                # Fetch all as a list
                data = []
                while 1:
                    d = self.fo()
                    if d is None:
                        break
                    data.append(dict(d))
            else:
                # Fetch all as OrderedDict under key
                data = OrderedDict()
                while 1:
                    d = self.fo()
                    if d is None:
                        break
                    data[d[key]] = d
        tools.check_request_timeout()  # Application hook to return 408 if time is over
        return data


    def gen_id(self, generator: str) -> int:
        # Generate Id
        query = ''' SELECT nextval('"s.{}"') AS "id" '''.format(generator)
        self.q(query)
        return self.fo()['id']


    def get_last_id(self, generator: str) -> int:
        # Get last id from generator
        query = ''' SELECT last_value AS "id" FROM "s.{}" '''.format(generator)
        self.q(query)
        return self.fo()['id']


    def set_gen_id(self, generator: str, value: int) -> int:
        # Set generator value
        query = ''' SELECT setval('"s.{}"', {}) '''.format(generator, value)
        return self.q(query)


    def get_table_fields(self, table: str) -> list:
        # Get list of table fields
        query = ''' SELECT * FROM "{}" LIMIT 1 '''.format(table)
        self.q(query)
        self.fo()
        return list(self.get_column_info().keys())


    def get_table_field_types(self, table: str) -> dict:
        # Get list of table field types
        query = ''' SELECT * FROM "{}" LIMIT 1 '''.format(table)
        self.q(query)
        self.fo()
        table_keys = self.get_column_info().keys()
        table_infos = self.get_column_info()
        fields = {}
        for field in table_keys:
            fields[field] = table_infos[field]['type']
        return fields
