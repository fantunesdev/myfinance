from types import SimpleNamespace

import pytest
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.test import Client, RequestFactory, override_settings
from django.urls import reverse

from login.models import Profile, User
from statement.context_processors import sidebar_navigation
from statement.models import Account, AccountType, Bank, Card, CardNumber, Flag


@pytest.fixture
def navigation_records(db):
    user = User.objects.create_user(username='sidebar-owner', name='Sidebar owner', email='owner@sidebar.invalid')
    other = User.objects.create_user(username='sidebar-other', name='Sidebar other', email='other@sidebar.invalid')
    Profile.objects.create(user=user)
    bank = Bank.objects.create(description='Sidebar bank')
    kind = AccountType.objects.create(description='Conta')
    own_account = Account.objects.create(user=user, bank=bank, type=kind)
    foreign_account = Account.objects.create(user=other, bank=bank, type=kind)
    flag = Flag.objects.create(description='Sidebar flag')
    cards = [Card.objects.create(user=owner, flag=flag, description=description,
                                 closing_day=3, expiration_day=10)
             for owner, description in ((user, 'Own card'), (other, 'Dependent card'), (other, 'Private card'))]
    for index, card in enumerate((cards[0], cards[1], cards[1])):
        CardNumber.objects.create(card=card, number=f'000{index}', dependente=user)
    return SimpleNamespace(user=user, account=own_account, foreign_account=foreign_account,
                           own_card=cards[0], dependent_card=cards[1], private_card=cards[2])


def test_sidebar_lists_only_own_accounts_and_authorized_cards(navigation_records):
    records = navigation_records
    request = RequestFactory().get('/usuarios/perfil/')
    request.user = records.user
    context = sidebar_navigation(request)
    assert list(context['extracts']) == [records.account]
    assert context['invoices'] == [records.own_card, records.dependent_card]


@pytest.mark.django_db
def test_anonymous_sidebar_has_no_data_or_queries(django_assert_num_queries):
    request = RequestFactory().get('/login/')
    request.user = AnonymousUser()
    with django_assert_num_queries(0):
        assert sidebar_navigation(request) == {}


@pytest.mark.parametrize('debug', [False, True])
@pytest.mark.parametrize('url', [
    '/usuarios/perfil/', '/usuarios/perfil/inatividade/editar/', '/',
    '/investimentos/', '/investimentos/conciliacao/',
])
def test_sidebar_links_exist_on_profile_forms_and_base_views(navigation_records, debug, url):
    records = navigation_records
    with override_settings(
        DEBUG=debug,
        ROOT_URLCONF='myfinance.urls',
        INSTALLED_APPS=[*settings.INSTALLED_APPS, 'django.contrib.admin', 'oauth2_provider'],
        ALLOWED_HOSTS=['testserver'],
        MIDDLEWARE=[
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
        ],
        TEMPLATES=[{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'APP_DIRS': True,
                    'OPTIONS': {'context_processors': [
                        'django.template.context_processors.request',
                        'django.contrib.auth.context_processors.auth',
                        'django.contrib.messages.context_processors.messages',
                        'statement.context_processors.sidebar_navigation',
                    ]}}],
    ):
        client = Client()
        client.force_login(records.user)
        response = client.get(url)
        assert response.status_code == 200
        html = response.content.decode()
        account_url = reverse('get_current_month_extract_by_account', args=[records.account.pk])
        assert f'href="{account_url}"' in html
        for card in (records.own_card, records.dependent_card):
            card_url = reverse('get_current_month_invoice_by_card', args=[card.pk])
            assert html.count(f'href="{card_url}"') == 1
        foreign_account_url = reverse('get_current_month_extract_by_account', args=[records.foreign_account.pk])
        private_card_url = reverse('get_current_month_invoice_by_card', args=[records.private_card.pk])
        assert f'href="{foreign_account_url}"' not in html
        assert f'href="{private_card_url}"' not in html
