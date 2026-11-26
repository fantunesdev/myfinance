"""MySQL integration tests with explicit test credentials; never loads .env."""
import os

from myfinance.test_settings import *  # noqa: F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'myfinance_tests',
        'USER': 'root',
        'PASSWORD': os.environ['MYFINANCE_TEST_MYSQL_PASSWORD'],
        'HOST': '127.0.0.1',
        'PORT': os.environ.get('MYFINANCE_TEST_MYSQL_PORT', '3306'),
        'OPTIONS': {'charset': 'utf8mb4'},
    },
}
