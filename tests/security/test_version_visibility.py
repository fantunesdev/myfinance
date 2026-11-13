from datetime import date

import pytest
from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import RequestFactory
from rest_framework.test import APIRequestFactory, force_authenticate

from api.views.default_views import Defaults
from login.context_processors import app_version
from login.models import User
from statement.models import Version


@pytest.mark.django_db
@pytest.mark.parametrize('method', ['get', 'head', 'options'])
def test_defaults_does_not_expose_version_anonymously(method):
    Version.objects.create(version='private-version', date=date.today())
    request = getattr(APIRequestFactory(), method)('/api/defaults/')
    response = Defaults.as_view()(request)
    assert response.status_code in (401, 403)
    assert 'private-version' not in response.render().content.decode()
    assert 'version' not in response.data


@pytest.mark.django_db
def test_authenticated_user_can_read_latest_version():
    Version.objects.create(version='old-version', date=date.today())
    Version.objects.create(version='current-version', date=date.today())
    user = User.objects.create(username='version-test')
    request = APIRequestFactory().get('/api/defaults/')
    force_authenticate(request, user=user)
    response = Defaults.as_view()(request)
    assert response.status_code == 200
    assert response.data['version'] == 'current-version'
    request.user = user
    assert app_version(request) == {'app_version': 'current-version'}


@pytest.mark.django_db
def test_anonymous_context_does_not_query_version(django_assert_num_queries):
    request = RequestFactory().get('/login/')
    request.user = AnonymousUser()
    with django_assert_num_queries(0):
        assert app_version(request) == {}


def test_login_page_has_no_version_or_defaults_script():
    request = RequestFactory().get('/login/')
    request.user = AnonymousUser()
    html = render_to_string('user/login.html', request=request)
    assert 'id="version"' not in html
    assert 'Versão:' not in html
    assert 'js/login.js' not in html
    assert '/api/defaults' not in html
