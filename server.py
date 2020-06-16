# -*- coding: UTF-8 -*-

import os
import uuid
from datetime import datetime, date
from collections import OrderedDict

import cherrypy
from formencode import validators, api as formencode_api

from lib.main import Invoker
from config.settings import app_config
from datanal.config.api_settings import api_config
from datanal.connector import get_connector_for_api
from datanal.analyzer import Analyzer
from datanal import tools as datanal_tools


# Setup routing manually
class Router(object):

    def __init__(self):
        self._data_src = None
        self._log = None


    @cherrypy.expose
    def ping(self):
        return 'pong'


    @property
    def data_src(self) -> str:
        if hasattr(self, '_data_src'):
            return getattr(self, '_data_src')
        raise RuntimeError


    @data_src.setter
    def data_src(self, value: str) -> None:
        validators.OneOf(api_config['data_sources']).to_python(value)
        self._data_src = value


    @property
    def log(self) -> bool:
        if hasattr(self, '_log'):
            return getattr(self, '_log')
        raise RuntimeError


    @log.setter
    def log(self, value: bool) -> None:
        validators.Bool().to_python(value)
        self._log = value


    @property
    def connector(self) -> object:
        return get_connector_for_api(self.data_src, self.log)


    @cherrypy.expose
    @cherrypy.tools.json_out()
    def start_watching(self) -> True:
        flag_file_path = os.path.normpath(os.path.join(
            app_config['path_storage'], 'tmp', 'watching_flag.txt'))
        with open(flag_file_path, 'w') as fh:
            fh.write('TRUE')
        return True


    @cherrypy.expose
    @cherrypy.tools.json_out()
    def finish_watching(self) -> True:
        flag_file_path = os.path.normpath(os.path.join(
            app_config['path_storage'], 'tmp', 'watching_flag.txt'))
        if os.path.exists(flag_file_path):
            os.unlink(flag_file_path)
        return True


    @cherrypy.expose(['watch-current-games'])
    @cherrypy.tools.json_out()
    def watch_current_games(self, data_src: str, game_name: str, log: bool = True) -> True:
        try:
            self.data_src = data_src
            self.log = log
            game_name = validators.OneOf(api_config['game_names']).to_python(game_name)
        except formencode_api.Invalid as exc:
            return str(exc)
        self.connector.watch_current_games(game_name)
        return True


    @cherrypy.expose(['collect-current-data'])
    @cherrypy.tools.json_out()
    def collect_current_data(self, data_src: str, game_name: str, log: bool = True) -> True:
        try:
            self.data_src = data_src
            self.log = log
            game_name = validators.OneOf(api_config['game_names']).to_python(game_name)
        except formencode_api.Invalid as exc:
            return str(exc)
        self.connector.collect_current_data(game_name)
        return True


    @cherrypy.expose(['analyze-current-data'])
    @cherrypy.tools.json_out()
    def analyze_current_data(
            self, data_src: str, game_name: str = None,
            data_src_tournament_id: int = None, log: bool = True) -> OrderedDict:
        try:
            self.data_src = data_src
            self.log = log
            if game_name is not None:
                game_name = validators.OneOf(api_config['game_names']).to_python(game_name)
            if data_src_tournament_id is not None:
                data_src_tournament_id = validators.Int(min=1).to_python(data_src_tournament_id)
        except formencode_api.Invalid as exc:
            return str(exc)
        return Analyzer().process_data('current', data_src, game_name, data_src_tournament_id)


    @cherrypy.expose(['download-current-data'])
    def download_current_data(self, output: str = 'csv', log: bool = True):
        try:
            self.log = log
            output = validators.OneOf(['csv', 'sql']).to_python(output)
        except formencode_api.Invalid as exc:
            return str(exc)

        tmp_file_path = os.path.normpath(os.path.join(
            app_config['path_storage'], 'tmp', str(uuid.uuid4())))
        if not datanal_tools.prepare_data_output('current', output, tmp_file_path):
            return False
        if output == 'csv':
            extension = 'zip'  # More CSV files are zipped in archive for download
            file_name = 'esport-current-{}.{}'.format(
                datetime.utcnow().strftime('%Y-%m-%d-%H-%M-%S'), extension)
        else:
            extension = 'sql'
            file_name = 'esport-current-{}.{}'.format(
                datetime.utcnow().strftime('%Y-%m-%d-%H-%M-%S'), extension)

        cherrypy.request.tmp_file_path = tmp_file_path
        cherrypy.request.hooks.attach('on_end_request', self._download_complete)
        return cherrypy.lib.static.serve_download(path=tmp_file_path, name=file_name)


    @cherrypy.expose(['garb-past-data'])
    @cherrypy.tools.json_out()
    def grab_past_data(self, data_src: str, game_name: str, date_from: date = None, date_to: date = None,
                       log: bool = True, delete_old: bool = True) -> OrderedDict:
        try:
            self.data_src = data_src
            self.log = log
            game_name = validators.OneOf(api_config['game_names']).to_python(game_name)
            if date_from:
                date_from = validators.DateValidator().to_python(date_from)
            if date_to:
                date_to = validators.DateValidator().to_python(date_to)
            if date_from and date_to:
                if datetime.strptime(date_from, "%Y-%m-%d") > datetime.strptime(date_to, "%Y-%m-%d"):
                    raise ValueError('Date from should be before date to')
                elif datetime.strptime(date_to, "%Y-%m-%d") > datetime.utcnow():
                    raise ValueError('Date to should be before in future')
            delete_old = validators.Bool().to_python(delete_old)
        except formencode_api.Invalid as exc:
            return str(exc)
        except ValueError as exc:
            return str(exc)
        return self.connector.grab_past_data(game_name, date_from, date_to, delete_old)


    @cherrypy.expose(['download-past-data'])
    def download_past_data(self, output: str = 'csv', log: bool = True):
        try:
            self.log = log
            output = validators.OneOf(['csv', 'sql']).to_python(output)
        except formencode_api.Invalid as exc:
            return str(exc)

        tmp_file_path = os.path.normpath(os.path.join(
            app_config['path_storage'], 'tmp', str(uuid.uuid4())))
        if not datanal_tools.prepare_data_output('past', output, tmp_file_path):
            return False
        if output == 'csv':
            extension = 'zip'  # More CSV files are zipped in archive for download
            file_name = 'esport-past-{}.{}'.format(
                datetime.utcnow().strftime('%Y-%m-%d-%H-%M-%S'), extension)
        else:
            extension = 'sql'
            file_name = 'esport-past-{}.{}'.format(
                datetime.utcnow().strftime('%Y-%m-%d-%H-%M-%S'), extension)

        cherrypy.request.tmp_file_path = tmp_file_path
        cherrypy.request.hooks.attach('on_end_request', self._download_complete)
        return cherrypy.lib.static.serve_download(path=tmp_file_path, name=file_name)


    @cherrypy.expose(['get-time-limit'])
    def get_time_limit(self) -> str:
        return datanal_tools.get_time_limit()


    @cherrypy.expose(['save-time-limit'])
    @cherrypy.tools.json_out()
    def save_time_limit(self, limit: int) -> True:
        try:
            limit = validators.Int(min=1).to_python(limit)
        except formencode_api.Invalid as exc:
            return str(exc)
        datanal_tools.save_time_limit(limit)
        return True


    @cherrypy.expose(['get-tournaments'])
    @cherrypy.tools.json_out()
    def get_tournaments(self, game_name: str) -> dict:
        try:
            game_name = validators.OneOf(api_config['game_names']).to_python(game_name)
        except formencode_api.Invalid as exc:
            return str(exc)
        return datanal_tools.get_tournaments(game_name)


    @cherrypy.expose(['save-tournaments'])
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def save_tournaments(self) -> True:
        try:
            game_name = validators.OneOf(api_config['game_names']).to_python(cherrypy.request.json['game_name'])
        except formencode_api.Invalid as exc:
            return str(exc)
        tournaments = cherrypy.request.json['tournaments']
        datanal_tools.save_tournaments(game_name, tournaments)
        return True


    @cherrypy.expose
    def monitor(self, data_src: str, log: bool = True) -> str:
        try:
            self.data_src = data_src
            self.log = log
        except formencode_api.Invalid as exc:
            return str(exc)
        res = self.connector.monitor()
        if res is False:
            return 'Monitoring was not successfull'
        return str(res)


    def _download_complete(self):
        os.unlink(cherrypy.request.tmp_file_path)


invoker = Invoker()

cherrypy.tree.mount(Router(), '/')

if __name__ == '__main__':
    invoker.cli_cmd()
else:
    application = invoker.wsgi_cmd()
