# -*- coding: UTF-8 -*-

import os

import toolz

from .default import config as default_config


config = {}

# Optional setting for development purposes
config['app_env'] = os.getenv('APP_ENV', 'prod')
config['app_log_factory'] = 'gcp'  # gcp, file, console
# config['app_log_threading'] = True  # default False
config['app_request_timeout'] = 590  # seconds, default 60
# config['path_storage'] = '{}{}'.format(os.path.join(instance_dirpath, '..', 'storage'), os.sep)
config['app_license_expiration'] = '2020-09-30'  # '2020-12-31', default None

app_config = toolz.dicttoolz.merge(default_config, config)
