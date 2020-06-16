# -*- coding: UTF-8 -*-

import sys
import platform
from datetime import datetime

import cherrypy
import toolz

from config.settings import app_config
from lib import tools as app_tools
from lib.libpool import LibPool


class Invoker(object):

    def __init__(self):
        self.logger = LibPool().logger


    def setup_server(self):
        self._set_config()
        self._set_cherrypy_hooks()


    def _set_config(self):
        default_config = {
            'tools.encode.on': True,
            'tools.encode.encoding': 'utf-8',
            # Prevents CherryPy Checker: The Application mounted at '' has an empty config.
            'checker.check_skipped_app_config': False,
            # Allow hooks
            'tools.on_start_resource.on': True,
            'tools.before_finalize.on': True,
            'tools.before_error_response.on': True,
            'tools.after_error_response.on': True,
            'tools.on_end_request.on': True
        }
        cherrypy.config.update(toolz.dicttoolz.merge(app_config['cherrypy'], default_config))


    def _set_cherrypy_hooks(self):
        cherrypy.tools.on_start_resource = cherrypy.Tool(
            'on_start_resource', app_tools.on_start_resource_wrapper)
        cherrypy.tools.before_finalize = cherrypy.Tool(
            'before_finalize', app_tools.before_finalize_wrapper)
        cherrypy.tools.before_error_response = cherrypy.Tool(
            'before_error_response', app_tools.before_error_response_wrapper)
        cherrypy.tools.after_error_response = cherrypy.Tool(
            'after_error_response', app_tools.after_error_response_wrapper)
        cherrypy.tools.on_end_request = cherrypy.Tool(
            'on_end_request', app_tools.on_end_request_wrapper)


    def cli_cmd(self):
        self.setup_server()
        cherrypy.config.update({'engine.autoreload.on': True})

        if platform.system() == 'Windows':
            # This enables Ctrl+C on Windows
            if hasattr(cherrypy.engine, 'signal_handler'):
                cherrypy.engine.signal_handler.subscribe()
            if hasattr(cherrypy.engine, 'console_control_handler'):
                cherrypy.engine.console_control_handler.subscribe()

        cherrypy.engine.start()
        if app_config['app_log_factory'] == 'gcp':
            self.logger.info('Starting Cherrypy server on "{}:{}" at "{}"\n'.format(
                app_config['cherrypy']['server.socket_host'],
                app_config['cherrypy']['server.socket_port'],
                datetime.strftime(datetime.utcnow(), '%Y-%m-%d %H:%M:%S')))
        cherrypy.engine.block()


    def wsgi_cmd(self):
        self.setup_server()
        cherrypy.config.update({
            'environment': 'embedded',
            'engine.autoreload.on': False
        })

        cherrypy.server.unsubscribe()
        sys.stdout = sys.stderr

        def application(environ, start_response):
            return cherrypy.tree(environ, start_response)
        return application
