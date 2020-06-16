# -*- coding: UTF-8 -*-

import sys
import os
import threading
import pkg_resources
import re
import traceback
from io import StringIO
import time
import datetime

import cherrypy

from lib.libpool import LibPool
from config.settings import app_config
from lib.sql.config.settings import db_config


logger = LibPool().logger  # Get application logger


def on_start_resource_wrapper():
    check_license_expiration()
    set_request_timeout_start()
    request_log()


def check_license_expiration() -> None:
    if (app_config['app_license_expiration'] and datetime.datetime.utcnow().date()
            > datetime.datetime.strptime(app_config['app_license_expiration'], '%Y-%m-%d').date()):
        cherrypy.request.show_tracebacks = False  # Disable traceback on Cherrypy html
        raise cherrypy.HTTPError(403, 'License expired')


def set_request_timeout_start() -> None:
    cherrypy.request._start = time.perf_counter()


def check_request_timeout() -> None:
    if time.perf_counter() - cherrypy.request._start >= app_config['app_request_timeout']:
        cherrypy.request.show_tracebacks = False  # Disable traceback on Cherrypy html
        raise cherrypy.HTTPError(408, 'Application Request Timeout')


def request_log():
    logdata = {
        'request_id': str(cherrypy.request.unique_id),
        'process_id': str(os.getpid()),
        'thread_id': str(threading.get_ident())
    }
    msg = '{} {}'.format(cherrypy.request.method, cherrypy.request.path_info)
    if cherrypy.request.query_string:
        msg += '?{}'.format(cherrypy.request.query_string)
    logger.info(msg, logdata)


def before_finalize_wrapper():
    secureheaders()


def secureheaders():
    # http://docs.cherrypy.org/en/latest/advanced.html#securing-your-server
    headers = cherrypy.response.headers
    headers['X-Frame-Options'] = 'DENY'
    headers['X-XSS-Protection'] = '1; mode=block'
    headers['Content-Security-Policy'] = "default-src 'self';"


def before_error_response_wrapper():
    rollback_trans_mode()


def rollback_trans_mode():
    try:
        # Is package installed
        pkg_resources.get_distribution('psycopg2')  # noqa
    except pkg_resources.DistributionNotFound:
        return

    if not hasattr(cherrypy.thread_data, 'dbconn') or cherrypy.thread_data.dbconn is None:
        # Do not rollback transaction without connection
        return
    else:
        conn = cherrypy.thread_data.dbconn
        if conn.autocommit is not False:
            # Do not rollback transaction without transaction mode, putconn back to Pool
            sql = LibPool().libsql
            sql.disconnect()
            return

    # If exception is raised during handling a request, rolllback transaction
    sql = LibPool().libsql
    sql.finish_trans_mode(action='rollback')
    sql.disconnect()


def after_error_response_wrapper():
    error_log()


def error_log():
    exc_type, exc_value, exc_traceback = sys.exc_info()
    result = re.match(r'''\<class '(?P<exc_type>[^']+)'\>''', str(exc_type))
    exc_type = result.group('exc_type')

    # Grab print exception output into variable
    old_stderr = sys.stderr
    output = StringIO()
    sys.stderr = output
    traceback.print_exception(exc_type, exc_value, exc_traceback)
    output_str = output.getvalue()
    sys.stderr = old_stderr

    logdata = {
        'request_id': str(cherrypy.request.unique_id),
        'process_id': str(os.getpid()),
        'thread_id': str(threading.get_ident()),
        'exec_time': str(round(time.perf_counter() - cherrypy.request._start, 3))
    }
    logger.critical('{}'.format(output_str), logdata)


def on_end_request_wrapper():
    disconnect_database()
    response_log()


def disconnect_database():
    try:
        # Is package installed
        pkg_resources.get_distribution('psycopg2')  # noqa
    except pkg_resources.DistributionNotFound:
        return

    if not hasattr(cherrypy.thread_data, 'dbconn') or cherrypy.thread_data.dbconn is None:
        # There is already no connection
        return
    else:
        conn = cherrypy.thread_data.dbconn
        sql = LibPool().libsql
        if conn.autocommit is False:
            # Rollback transaction mode, need to be done before disconnect
            sql.finish_trans_mode(action='rollback')

        # On the end of request, putconn back to Pool
        sql.disconnect()


def response_log():
    exec_time = round(time.perf_counter() - cherrypy.request._start, 3)
    status = cherrypy.response.status
    if status is None:
        # 1. Application start forbidden multiprocessing which kidnap Cherrypy controlled process and this is response
        # 2. Uncaught exception
        logdata = {
            'request_id': str(cherrypy.request.unique_id),
            'process_id': str(os.getpid()),
            'thread_id': str(threading.get_ident()),
            'exec_time': str(exec_time)
        }
        logger.error('response_log(): without status', logdata)
        return

    if isinstance(status, str):
        status_code = int(status.split(' ')[0])
    else:
        status_code = status

    logdata = {
        'request_id': str(cherrypy.request.unique_id),
        'process_id': str(os.getpid()),
        'thread_id': str(threading.get_ident()),
        'status': str(status_code),
        'exec_time': str(exec_time)
    }

    if status_code >= 400 and status_code < 500:
        logger.warning('{} {} {}?{} {}s'.format(
            status, cherrypy.request.method, cherrypy.request.path_info, cherrypy.request.query_string, exec_time),
            logdata)
    elif status_code >= 500:
        logger.error('{} {} {}?{} {}s'.format(
            status, cherrypy.request.method, cherrypy.request.path_info, cherrypy.request.query_string, exec_time),
            logdata)
    else:
        logger.info('{} {} {}?{} {}s'.format(
            status, cherrypy.request.method, cherrypy.request.path_info, cherrypy.request.query_string, exec_time),
            logdata)


def psql_execute_database_script(sql_filepath: str, database: str = None) -> bool:
    if not database:
        sql = LibPool().libsql
        database = sql.active_database
    kwargs = db_config['database'][database]
    kwargs['log_file'] = '{}{}datanal_sql.log'.format(os.path.join(app_config['path_storage'], 'log'), os.sep)
    cmd = 'psql --file={} --quiet --log-file={log_file}'.format(sql_filepath)
    cmd += ' --dbname=postgresql://{user}:{password}@{host}:{port}/{dbname}'''.format(
        **kwargs)
    if os.system(cmd) == 0:
        return True
    return False
