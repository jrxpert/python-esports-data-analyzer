# -*- coding: UTF-8 -*-

import requests
import time

import cherrypy

from lib.libpool import LibPool
from lib import tools
from datanal.config.api_settings import api_config
from datanal.connector import RestClientInterface
from datanal.tools import to_json
from datanal.client.provider1pool import Provider1Pool


class AuthenticationError(Exception):
    pass


class RestClient(RestClientInterface):
    '''Define concrete Adapter
    '''
    _name = 'provider1'
    _abiospool = Provider1Pool()

    def __init__(self, *args, **kwargs):
        cherrypy.thread_data.client_obj = self
        if 'log' in kwargs:
            self._log = kwargs['log']
        super().__init__(*args, **kwargs)


    def _logging(self, message: str, url: str = None, log_type: str = None, log_data: dict = {}) -> None:
        if self._log:
            api_config[self._name]['log'] = True
        if api_config[self._name]['log'] is False:
            return
        if not hasattr(self, 'logger'):
            self.logger = LibPool().logger
        logdata = log_data
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
        auth_token = self._abiospool.auth_token
        if auth_token is None:
            # Auth token does not exists, get new one
            self.authenticate()
            auth_token = self._abiospool.auth_token
            if auth_token is None:
                error_message = 'Cannot connect to Provider 2'
                self._logging(error_message, log_type='error')
                raise cherrypy.HTTPError(401, error_message)

        ac = api_config[self._name]
        url_start = '{}{}?'.format(ac['url'], api_endpoint)
        if '?' in api_endpoint:
            url_start = '{}&'.format(url_start[0:-1])
        url = '{}access_token={}'.format(url_start, auth_token)
        if self._abiospool.request_permission:
            response = requests.get(url, data=to_json(data))
        if response.status_code == 401 and response.json()['error_description'] == 'Access token is not valid.':
            # Unauthorized -> authenticate & repeat request
            error_message = 'Provider 2 Unauthorized: {} {}'.format(response.json()['error_description'], auth_token)
            self._logging(error_message, url, 'error')
            info_message = 'Reconnect to Provider 2'
            self._logging(info_message)
            self.authenticate()
            response = requests.get(url, data=to_json(data))

        tools.check_request_timeout()  # Application hook to return 408 if time is over
        return response.headers, response.json()


    def authenticate(self) -> None:
        ac = api_config[self._name]
        auth_data = {
            'grant_type': 'client_credentials',
            'client_id': ac['client_id'],
            'client_secret': ac['client_secret']
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        url = '{}{}'.format(ac['url'], 'oauth/access_token')
        try:  # Authenticate
            response = requests.post(url, data=auth_data, headers=headers)
            if 'error' in response.json():
                raise AuthenticationError(response.json()['error_description'])

            self._abiospool.auth_token = response.json()['access_token']
        except Exception as e:
            error_message = 'Authenticate to Provider 2 was not succesfull: {}'.format(e)
            self._logging(error_message, url, 'error')
            raise cherrypy.HTTPError(401, error_message)


    def monitor(self) -> float:
        # Try to authenticate at REST endpoint
        start_time = time.perf_counter()
        if self.authenticate() is False:
            return False
        return time.perf_counter() - start_time
