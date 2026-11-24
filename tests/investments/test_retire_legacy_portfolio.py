from datetime import date
from importlib import import_module

import pytest
from django.apps import apps
from django.conf import settings
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.test import Client, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import NoReverseMatch, reverse

from login.models import Profile, User
from statement.models import Account, AccountType, Bank, Currency

LEGACY_MODELS = (
    'Index',
    'IndexHistoricalSeries',
    'FixedIncomeSecurity',
    'FixedIncome',
    'Ticker',
    'Sector',
    'VariableIncome',
    'AssetTransaction',
)


@pytest.mark.django_db
def test_retirement_removes_models_from_state_without_changing_historical_records():
    loader = MigrationLoader(connection)
    state = loader.project_state([('statement', '0026_dreamdocument')])

    def create(model, **values):
        return state.apps.get_model('statement', model).objects.create(**values)

    user = User.objects.create(username='archived-portfolio', email='archive@test.invalid')
    Currency.objects.get_or_create(pk='BRL', defaults={'description': 'Real', 'symbol': 'R$'})
    bank = Bank.objects.create(description='Banco')
    kind = AccountType.objects.create(description='Conta')
    account = Account.objects.create(user=user, bank=bank, type=kind)
    index = create('Index', description='CDI', bcb_id=13)
    create('IndexHistoricalSeries', index_id=index.pk, date=date(2020, 1, 1), rate=4.5)
    security = create('FixedIncomeSecurity', description='Certificado', abbreviation='CDB')
    create(
        'FixedIncome',
        account_id=account.pk,
        principal=1000,
        security_id=security.pk,
        investment_date=date(2020, 1, 1),
        maturity_date=date(2022, 1, 1),
        index_id=index.pk,
        contractual_rate=100,
        user_id=user.pk,
    )
    create('Sector', description='Tecnologia')
    ticker = create('Ticker', description='Ação', code='TEST3')
    asset = create('VariableIncome', account_id=account.pk, ticker_id=ticker.pk, user_id=user.pk)
    create(
        'AssetTransaction',
        variable_income_id=asset.pk,
        quantity=10,
        value=100,
        transaction_type='buy',
        date=date(2020, 1, 1),
    )
    models = [state.apps.get_model('statement', name) for name in LEGACY_MODELS]
    snapshot = {model._meta.db_table: list(model.objects.values()) for model in models}
    migration = import_module('statement.migrations.0027_retire_legacy_portfolio').Migration('0027', 'statement')

    with CaptureQueriesContext(connection) as queries:
        retired_state = migration.apply(state, connection.schema_editor(atomic=False))

    assert not any(query['sql'].lstrip().upper().startswith(('DROP ', 'ALTER ', 'DELETE ')) for query in queries)
    for name in LEGACY_MODELS:
        with pytest.raises(LookupError):
            retired_state.apps.get_model('statement', name)
        with pytest.raises(LookupError):
            apps.get_model('statement', name)
    for model in models:
        assert list(model.objects.values()) == snapshot[model._meta.db_table]
    assert set(snapshot) <= set(connection.introspection.table_names())


@pytest.fixture
def web(db):
    with override_settings(
        ROOT_URLCONF='myfinance.urls',
        INSTALLED_APPS=[*settings.INSTALLED_APPS, 'django.contrib.admin', 'oauth2_provider'],
        ALLOWED_HOSTS=['testserver'],
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
            username='current-investments', name='Current investments', email='current@test.invalid', is_staff=True
        )
        Profile.objects.create(user=user)
        client = Client()
        client.force_login(user)
        yield client


@pytest.mark.parametrize(
    'url',
    [
        '/carteira/',
        '/carteira/renda_fixa/',
        '/carteira/renda_variavel/',
        '/api/fixed-income/progression/',
        '/relatorio_financeiro/configuracoes/indices/cadastrar/',
        '/relatorio_financeiro/configuracoes/setor/cadastrar/',
        '/relatorio_financeiro/configuracoes/papel/cadastrar/',
    ],
)
def test_legacy_routes_are_no_longer_exposed(web, url):
    assert web.get(url).status_code == 404


def test_current_investments_and_settings_do_not_query_legacy_tables(web):
    legacy_tables = [f'statement_{name.lower()}' for name in LEGACY_MODELS]
    for name in ['investments_dashboard', 'setup_settings']:
        with CaptureQueriesContext(connection) as queries:
            response = web.get(reverse(name))
        assert response.status_code == 200
        assert not any(table in query['sql'] for query in queries for table in legacy_tables)
        assert '/investimentos/' in response.content.decode()
    with pytest.raises(NoReverseMatch):
        reverse('get_portfolio')
