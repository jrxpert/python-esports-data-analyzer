# -*- coding: UTF-8 -*-

import os


db_config = {
    'default': 'database-production',
    'database': {
        'database-production': {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', 5432),
            'dbname': os.getenv('DB_NAME', 'production'),
            'user': os.getenv('DB_USERNAME', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'postgres'),
            'maxconn': os.getenv('DB_MAXCONN', 20),
            'log': os.getenv('DB_LOG', False)
        },
        'database-test': {
            'host': os.getenv('TEST_DB_HOST', 'localhost'),
            'port': os.getenv('TEST_DB_PORT', 5432),
            'dbname': os.getenv('TEST_DB_NAME', 'test'),
            'user': os.getenv('TEST_DB_USERNAME', 'postgres'),
            'password': os.getenv('TEST_DB_PASSWORD', 'postgres'),
            'maxconn': os.getenv('TEST_DB_MAXCONN', 10),
            'log': os.getenv('TEST_DB_LOG', False)
        }
    }
}
