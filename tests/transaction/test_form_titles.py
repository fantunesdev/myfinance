from datetime import date
from html.parser import HTMLParser
from types import SimpleNamespace

import pytest
from django.conf import settings
from django.forms import Form
from django.template.loader import render_to_string
from django.test import Client, RequestFactory, override_settings
from django.urls import reverse

from investments.models import Asset
from login.models import Profile, User
from statement.models import (Card, Category, Currency, Device, Dream,
                              FixedExpenses, Flag, Index, Subcategory,
                              Transaction)


class Titles(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.title = ''
        self.heading = ''
        self.current = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == 'title':
            self.current = 'title'
        elif tag == 'h3' and not self.heading and 'box-title' in dict(attrs).get('class', '').split():
            self.current = 'heading'

    def handle_data(self, data):
        if self.current:
            setattr(self, self.current, getattr(self, self.current) + data)

    def handle_endtag(self, tag):
        if tag in {'title', 'h3'}:
            self.current = None


def assert_titles(html, expected):
    parsed = Titles(html)
    assert ' '.join(parsed.title.split()).removesuffix(' | MyFinance') == expected
    assert ' '.join(parsed.heading.split()).startswith(expected)


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
        TEMPLATES=[{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'APP_DIRS': True,
                    'OPTIONS': {'context_processors': [
                        'django.template.context_processors.request',
                        'django.contrib.auth.context_processors.auth',
                        'django.contrib.messages.context_processors.messages',
                    ]}}],
    ):
        user = User.objects.create_user(username='form-titles', name='Form titles', email='titles@test.invalid', is_staff=True)
        Profile.objects.create(user=user)
        client = Client()
        client.force_login(user)
        yield client, user


@pytest.fixture
def records(web):
    client, user = web
    Currency.objects.get_or_create(pk='BRL', defaults={'description': 'Real', 'symbol': 'R$'})
    category = Category.objects.create(description='Categoria', type='saida')
    subcategory = Subcategory.objects.create(description='Subcategoria', category=category)
    transaction = Transaction.objects.create(
        user=user, category=category, subcategory=subcategory, description='Lançamento existente',
        value=100, posted_date=date(2026, 11, 24), payment_date=date(2026, 11, 24),
    )
    flag = Flag.objects.create(description='Bandeira')
    return SimpleNamespace(
        client=client,
        transaction=transaction,
        device=Device.objects.create(user=user, name='Dispositivo'),
        dream=Dream.objects.create(user=user, description='Sonho'),
        card=Card.objects.create(user=user, flag=flag, description='Cartão', closing_day=5, expiration_day=10),
        fixed_expense=FixedExpenses.objects.create(user=user, description='Despesa', start_date=date(2026, 1, 1)),
        index=Index.objects.create(description='Índice'),
        asset=Asset.objects.create(user=user, description='Ativo', asset_type='fixed_income'),
    )


@pytest.mark.parametrize('create_name,create_args,update_name,record,entity', [
    ('create_transaction', ['saida'], 'update_transaction', 'transaction', 'Lançamento'),
    ('create_device', [], 'update_device', 'device', 'Device'),
    ('create_dream', [], 'update_dream', 'dream', 'Sonhos'),
    ('create_card', [], 'update_card', 'card', 'Cartão'),
    ('create_fixed_expense', [], 'update_fixed_expense', 'fixed_expense', 'Despesa Fixa'),
    ('create_index', [], 'update_index', 'index', 'Índice'),
    ('create_asset', [], 'update_asset', 'asset', 'Ativos'),
])
@pytest.mark.parametrize('method', ['get', 'post'])
def test_create_and_edit_titles_including_invalid_submissions(records, create_name, create_args, update_name, record, entity, method):
    for url, action in [
        (reverse(create_name, args=create_args), 'Cadastrar'),
        (reverse(update_name, args=[getattr(records, record).pk]), 'Editar'),
    ]:
        response = getattr(records.client, method)(url, {'description': ''})
        assert response.status_code == 200
        assert_titles(response.content.decode(), f'{action} {entity}')
        if method == 'post':
            assert response.context['form'].errors


@pytest.mark.parametrize('template,entity', [
    ('portion/portion_form.html', 'Parcela'),
    ('fixed_expenses/fixed_expenses_form.html', 'Despesa Fixa'),
    ('fixed_income/form.html', 'Ativo de Renda Fixa'),
    ('fixed_income/security/security_form.html', 'Ativo de Renda Fixa'),
    ('fixed_income/index/index_form.html', 'Índice'),
])
@pytest.mark.parametrize('create', [False, True])
def test_custom_form_titles_follow_mode_instead_of_url(web, template, entity, create):
    request = RequestFactory().get('/rota-sem-indicacao-da-operacao/')
    request.user = web[1]
    html = render_to_string(template, {'create': create, 'form': Form()}, request=request)
    assert_titles(html, f'{"Cadastrar" if create else "Editar"} {entity}')


@pytest.mark.parametrize('url_name,expected', [
    ('create_user', 'Cadastrar Usuário'),
    ('update_profile', 'Editar Perfil'),
    ('change_password', 'Alterar Senha'),
    ('update_next_month_view', 'Editar Configuração - Próximo Mês'),
    ('update_fuel_tracking', 'Editar Configuração - Combustível'),
    ('edit_inactivity_logout', 'Editar Privacidade e segurança'),
])
def test_user_and_settings_forms_have_consistent_titles(web, url_name, expected):
    response = web[0].get(reverse(url_name))
    assert response.status_code == 200
    assert_titles(response.content.decode(), expected)
