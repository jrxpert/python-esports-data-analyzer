# -*- coding: UTF-8 -*-

import time
import threading

from datanal.config.api_settings import api_config


class Provider2Pool(object):
    _request_start = None
    _request_permission = True

    def __init__(self):
        self._lock = threading.Lock()


    @property
    def request_permission(self) -> str:
        self._lock.acquire()
        try:
            self._request_start = time.perf_counter()
            if self._request_permission is not True:
                self.request_permission = True
            self.request_permission = False
            return True
        finally:
            self._request_start = None
            self._lock.release()


    @request_permission.setter
    def request_permission(self, value: bool) -> None:
        if value is True:
            while ((time.perf_counter() - self._request_start)
                    < (1 / api_config['provider2']['requests_per_second'])):
                time.sleep(0.1)
        self._request_permission = value
