"""Isolated settings for tests: no .env, external database, Redis or network."""
SECRET_KEY = 'isolated-tests-only'
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'login',
    'statement',
    'investments',
    'rest_framework',
]
AUTH_USER_MODEL = 'login.User'
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
ROOT_URLCONF = 'investments.urls'
USE_TZ = True
TIME_ZONE = 'America/Sao_Paulo'
STATIC_URL = '/static/'
REST_FRAMEWORK = {'DEFAULT_AUTHENTICATION_CLASSES': [], 'DEFAULT_PERMISSION_CLASSES': []}
MIDDLEWARE = []
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'APP_DIRS': True}]
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
