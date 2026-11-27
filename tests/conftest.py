from types import SimpleNamespace

import pytest
from django.conf import settings
from django.test import Client, override_settings

from login.models import Profile, User


@pytest.fixture
def authenticated_web(db, tmp_path):
    with override_settings(
        ROOT_URLCONF='myfinance.urls',
        INSTALLED_APPS=[*settings.INSTALLED_APPS, 'django.contrib.admin', 'oauth2_provider'],
        ALLOWED_HOSTS=['testserver'],
        LOGIN_URL='/login/',
        MEDIA_ROOT=tmp_path,
        CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}},
        MIDDLEWARE=[
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
        ],
        TEMPLATES=[
            {
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
                'APP_DIRS': True,
                'OPTIONS': {
                    'context_processors': [
                        'django.template.context_processors.request',
                        'django.contrib.auth.context_processors.auth',
                        'django.contrib.messages.context_processors.messages',
                    ]
                },
            }
        ],
    ):
        user = User.objects.create_user(
            username='web-coverage',
            email='coverage@web.invalid',
            name='Coverage',
            password='Coverage!123',
            is_staff=True,
        )
        Profile.objects.create(user=user)
        client = Client()
        client.force_login(user)
        yield SimpleNamespace(user=user, client=client)
