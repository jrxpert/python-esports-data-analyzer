# -*- coding: UTF-8 -*-

import requests
import time

import cherrypy

from lib.libpool import LibPool
from lib import tools
from datanal.config.api_settings import api_config
from datanal.connector import RestClientInterface
from datanal.tools import to_json
from datanal.client.provider2pool import Provider2Pool


class AuthenticationError(Exception):
    pass


class RestClient(RestClientInterface):
    '''Define concrete Adapter
    '''
    _name = 'provider2'
    _pandapool = Provider2Pool()

    def __init__(self, *args, **kwargs):
        cherrypy.thread_data.client_obj = self
        if 'log' in kwargs:
            self._log = kwargs['log']
        super().__init__(*args, **kwargs)


    def _logging(self, message: str, url: str = None, log_type: str = None) -> None:
        if self._log:
            api_config[self._name]['log'] = True
        if api_config[self._name]['log'] is False:
            return
        if not hasattr(self, 'logger'):
            self.logger = LibPool().logger
        logdata = {
            'connection_details': api_config[self._name]
        }
        if url:
            logdata['url'] = url
        if log_type is not None and log_type == 'error':
            self.logger.error(message, logdata)
        else:
            self.logger.info(message, logdata)


    def send_request(self, api_endpoint: str, data: dict = {}) -> dict:
        ac = api_config[self._name]
        url_start = '{}{}?'.format(ac['url'], api_endpoint)
        if '?' in api_endpoint:
            url_start = '{}&'.format(url_start[0:-1])
        url = '{}token={}'.format(url_start, ac['auth_token'])
        try:
            if self._pandapool.request_permission:
                response = requests.get(url, data=to_json(data))
            if response.status_code == 401:
                raise AuthenticationError(response.json()['error'])
            elif 'error' in response.json():
                raise Exception(response.json()['error'])
        except AuthenticationError as e:
            error_message = 'Authentication error on Provider 1: {}'.format(e)
            self._logging(error_message, url, 'error')
            raise cherrypy.HTTPError(401, error_message)
        except Exception as e:
            error_message = 'Request to Provider 1 was not succesfull: {}'.format(e)
            self._logging(error_message, url, 'error')
            raise cherrypy.HTTPError(500, error_message)

        tools.check_request_timeout()  # Application hook to return 408 if time is over
        return response.headers, response.json()


    def authenticate(self) -> None:
        # Provider 1 is always authenticated, hit lives matches to check it
        url = '{}{}'.format(api_config[self._name]['url'], 'lives')
        response = requests.get(url)
        if response.status_code == 401:
            return False


    def monitor(self) -> float:
        # Try to authenticate at REST endpoint
        start_time = time.perf_counter()
        if self.authenticate() is False:
            return False
        return time.perf_counter() - start_time
