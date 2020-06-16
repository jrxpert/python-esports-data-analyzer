# -*- coding: UTF-8 -*-

import os

from config.__init__ import __version__


# Full dirpath to the conf directory
conf_dirpath = '{}{}'.format(os.path.dirname(os.path.abspath(__file__)), os.sep)

# Full dirpath to the instance directory
instance_dirpath = '{}{}'.format(os.path.join(conf_dirpath, '..'), os.sep)

# Full dirpath to the data directory with files necessary for this app, for example static.
# data_dirpath = '{}{}'.format(os.path.join(app_dirpath, '..', 'data'), os.sep)

# Full dirpath to the storage directory with logs, file storage, session files...
# If app is updated to a newer revision, data can be different (static),
# storage can be kept the same - same logs, same sessions.
storage_dirpath = '{}{}'.format(os.path.join(instance_dirpath, '..', 'storage'), os.sep)


config = {}
config['app_name'] = 'datanal'
config['app_version'] = __version__
config['app_env'] = 'dev'
config['app_log_factory'] = 'console'  # gcp, file, console
config['app_log_threading'] = False
config['app_request_timeout'] = 60  # seconds
config['app_license_expiration'] = None  # '2020-12-31'

config['path_conf'] = conf_dirpath
config['path_instance'] = instance_dirpath
# config['path_data'] = data_dirpath
config['path_storage'] = storage_dirpath

config['cherrypy'] = {
    'server.socket_host': '127.0.0.1',
    'server.socket_port': 8080,
    'server.thread_pool': 4,
    'server.max_request_body_size': 0,
    'server.socket_timeout': 2,  # 10
    'tools.sessions.timeout': 60,
    'tools.decode.on': True,
    'tools.trailing_slash.on': False,
    'log.error_file': '',
    'log.access_file': '',
    'tools.log_request_data.on': False
}
