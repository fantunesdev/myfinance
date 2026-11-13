"""Real HTTP/browser tests, using only disposable data under /tmp."""
import os
from pathlib import Path

from myfinance.test_settings import *  # noqa: F403

BASE_DIR = Path(__file__).resolve().parent.parent
TEST_DIRECTORY = Path(os.environ['MYFINANCE_E2E_DIRECTORY']).resolve()
if not TEST_DIRECTORY.is_relative_to('/tmp'):
    raise ValueError('Browser tests require a disposable directory under /tmp.')
DEBUG = False
LANGUAGE_CODE = 'pt-br'
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'testserver']
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': TEST_DIRECTORY / 'db.sqlite3'}}
MEDIA_ROOT = TEST_DIRECTORY / 'media'
MEDIA_URL = '/media/'
STATIC_ROOT = TEST_DIRECTORY / 'static'
INSTALLED_APPS = [*INSTALLED_APPS, 'django.contrib.admin', 'oauth2_provider']  # noqa: F405
ROOT_URLCONF = 'myfinance.urls'
LOGIN_URL = '/login/'
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'login.middleware.PrivatePageCacheMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'APP_DIRS': True,
              'OPTIONS': {'context_processors': [
                  'django.template.context_processors.request',
                  'django.contrib.auth.context_processors.auth',
                  'login.context_processors.inactivity_logout',
                  'django.contrib.messages.context_processors.messages',
              ]}}]
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'statement.authentication.DeviceTokenAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'oauth2_provider.contrib.rest_framework.OAuth2Authentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
}
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': f'django.contrib.auth.password_validation.{name}'}
    for name in ('UserAttributeSimilarityValidator', 'MinimumLengthValidator',
                 'CommonPasswordValidator', 'NumericPasswordValidator')
]
PASSWORD_HASHERS = ['django.contrib.auth.hashers.PBKDF2PasswordHasher']
CHANNEL_LAYERS = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
ACCESS_TOKEN_EXPIRE_MINUTES = 15
ALGORITHM = 'HS256'
ENVIRONMENT = 'security-tests'
