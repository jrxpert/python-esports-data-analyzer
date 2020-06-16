# -*- coding: UTF-8 -*-

import logging
import threading
import os
import sys
import re
import traceback
from io import StringIO
import logging.config
from typing import NewType

import cherrypy
import google.cloud.logging
from google.cloud.logging.handlers import CloudLoggingHandler, setup_logging
import toolz

from config.settings import app_config


ObjectStr = NewType('ObjectStr', (object, str))

# logger = setup_logger()
# logger.info('testujeme INFO')
# logger.warning('testujeme WARNING')
# logger.error('testujeme ERROR')

# http://docs.cherrypy.org/en/latest/basics.html#logging
LOG_CONFIG = {
    'version': 1,
    'formatters': {
        'void': {
            'format': ''
        },
        'message': {
            'format': '%(message)s'
        },
        'standard': {
            # 'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s' - [INFO] root: - > [INFO]
            'format': '%(asctime)s [%(levelname)s] %(message)s'  # Used for console logging
        },
        'app': {
            'format': '%(asctime)s [%(levelname)s] %(message)s'
        }
    },
    'handlers': {
        'default': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'stream': 'ext://sys.stdout'
        },
        'cherrypy_console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'void',
            'stream': 'ext://sys.stdout'
        },
        'cherrypy_access': {
            'level': 'INFO',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'formatter': 'void',
            'filename': os.path.join(app_config['path_storage'], 'log', 'access.log'),
            'when': 'midnight',
            'encoding': 'utf8'
        },
        'cherrypy_error': {
            'level': 'INFO',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'formatter': 'void',
            'filename': os.path.join(app_config['path_storage'], 'log', 'error.log'),
            'when': 'midnight',
            'encoding': 'utf8'
        },
        'app_file': {
            'level': 'INFO',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'formatter': 'app',
            'filename': os.path.join(app_config['path_storage'], 'log', 'app.log'),
            'when': 'midnight',
            'encoding': 'utf8'
        }
    },
    'loggers': {
        '': {
            'handlers': ['default'],
            'level': 'INFO'
        },
        'cherrypy.access': {
            'handlers': ['cherrypy_access'],
            'level': 'INFO',
            'propagate': False
        },
        'cherrypy.error': {
            'handlers': ['cherrypy_error'],
            'level': 'INFO',
            'propagate': False
        },
        'app': {
            'handlers': ['app_file'],
            'level': 'INFO',
            'propagate': False
        }
    }
}


def setup_logger() -> object:
    '''Setup main application logger
    '''

    # Setup uncaught exception handler
    default_exception_handler()

    if app_config['app_log_factory'] == 'gcp' and os.getenv('GOOGLE_APPLICATION_CREDENTIALS') is None:
        app_config['app_log_factory'] = 'file'  # Prevent set up GCP logging without credentials ENV variable
        logging.error('GOOGLE_APPLICATION_CREDENTIALS ENV variable is missing, logging set to file output')

    if app_config['app_log_factory'] == 'gcp':
        # Disable whole cherrypy console logging
        cherrypy.log.screen = False
        logging.getLogger("cherrypy").propagate = False

        # Connect GCP logging to default Python logger
        logger = logging.getLogger()

        # Remove original log handlers
        for handler in logger.handlers:
            logger.removeHandler(handler)

        # Setup Google Cloud Logging
        client = google.cloud.logging.Client()

        # Setup CloudLoggingHandler(logging.StreamHandler) handler explicitly with Custom GCP Formatter
        handler = CloudLoggingHandler(
            client, labels={'app_name': app_config['app_name'], 'app_version': app_config['app_version'],
                            'app_environment': app_config['app_env']})
        handler.setFormatter(CustomGCPFormatter())

        # Setup Python logger explicitly with custom handler
        setup_logging(handler)

    elif app_config['app_log_factory'] == 'file':
        # Load log configuration
        logging.config.dictConfig(LOG_CONFIG)

        # Custom app logger
        logger = logging.getLogger('app')

    else:
        # Load log configuration
        logging.config.dictConfig(LOG_CONFIG)

        # Custom app logger
        logger = logging.getLogger()

    return logger


class CustomGCPFormatter(logging.Formatter):

    def format(self, record: object) -> ObjectStr:
        new_record = {}
        new_record['msg'] = record.msg

        # Always set request id
        if not record.args or 'request_id' not in record.args.keys():
            new_record['request_id'] = str(cherrypy.request.unique_id)

        if record.args:
            # Set arguments
            for key, value in record.args.items():
                if isinstance(value, dict):
                    values = self._force_string_values(value, key)
                    new_record = toolz.dicttoolz.merge(new_record, values)
                else:
                    new_record[key] = str(value)

            if app_config['app_log_threading'] is False:
                # Unset threading info
                if 'process_id' in new_record:
                    del(new_record['process_id'])
                if 'thread_id' in new_record:
                    del(new_record['thread_id'])

        if app_config['app_log_threading'] is True:
            # Set threading info
            if 'process_id' not in new_record:
                new_record['process_id'] = str(os.getpid())
            if 'thread_id' not in new_record:
                new_record['thread_id'] = str(threading.get_ident())

        return new_record


    def _force_string_values(self, params: dict, name: str) -> dict:
        d = {}
        for key, value in params.items():
            if isinstance(value, dict):
                values = self._force_string_values(value, key)
                d = toolz.dicttoolz.merge(d, values)
            else:
                d['{}_{}'.format(key, name)] = str(value)
        return d


def default_exception_handler():
    '''Handle unhandled exceptions - log them to error log.

    https://stackoverflow.com/questions/6234405/logging-uncaught-exceptions-in-python
    '''
    def handle_unhandled_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return None

        result = re.match(r'''\<class '(?P<exc_type>[^']+)'\>''', str(exc_type))
        exc_type = result.group('exc_type')

        # Grab printed exception output into variable
        old_stderr = sys.stderr
        output = StringIO()
        sys.stderr = output
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        output_str = output.getvalue()
        sys.stderr = old_stderr

        logger = logging.getLogger()
        logger.critical('{}'.format(output_str))

    sys.excepthook = handle_unhandled_exception
