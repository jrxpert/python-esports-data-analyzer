# -*- coding: UTF-8 -*-

import toolz

from .default import config as default_config


config = {}

# Optional setting for development purposes
config['app_log_factory'] = 'gcp'  # gcp, file, console
# config['app_log_threading'] = True  # default False
# config['app_request_timeout'] = 120  # seconds, default 60
# config['path_storage'] = '{}{}'.format(os.path.join(instance_dirpath, '..', 'storage'), os.sep)
# config['app_license_expiration'] = None  # '2020-12-31', default None

config['cherrypy'] = {
    'server.socket_host': '127.0.0.1',
    'server.socket_port': 8080,
    'server.thread_pool': 2,  # For development is one Thread better because of server restarts after code changes
}

app_config = toolz.dicttoolz.merge(default_config, config)
