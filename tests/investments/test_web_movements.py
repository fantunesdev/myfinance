from datetime import date
from types import SimpleNamespace

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from investments.models import Asset, Broker, Investment, InvestmentTransaction
from investments.services.investment import InvestmentService
from investments.services.transaction import InvestmentTransactionService as Service


@pytest.fixture
def portfolio(authenticated_web):
    user = authenticated_web.user
    wallet = Service.get_or_create_default_wallet(user)
    asset = Asset.objects.create(user=user, description='CDB de teste', asset_type='fixed_income')
    holding = Investment.objects.create(
        user=user, asset=asset, broker=wallet.broker, description='CDB', start_date=date(2020, 1, 1)
    )
    credit = InvestmentTransaction.objects.create(
        user=user, investment=wallet, type='aporte', amount=1000, date=date(2020, 1, 1)
    )
    purchase = InvestmentTransaction.objects.create(
        user=user, investment=holding, type='aporte', amount=500, date=date(2020, 1, 1)
    )
    return SimpleNamespace(
        user=user, client=authenticated_web.client, wallet=wallet, holding=holding, credit=credit, purchase=purchase
    )


@pytest.mark.parametrize(
    'route, target',
    [
        ('apply_investment_from_wallet', 'holding'),
        ('redeem_investment_to_wallet', 'holding'),
        ('apply_from_wallet_transaction', 'credit'),
        ('redeem_from_investment_transaction', 'purchase'),
    ],
)
def test_movement_forms_render_existing_investment_context(portfolio, route, target):
    p = portfolio
    response = p.client.get(reverse(route, args=[getattr(p, target).pk]))
    assert response.status_code == 200
    assert response.context['form'] is not None


@pytest.mark.parametrize(
    'route, target',
    [
        ('apply_investment_from_wallet', 'holding'),
        ('apply_from_wallet_transaction', 'credit'),
    ],
)
def test_wallet_application_creates_a_balanced_transfer(portfolio, route, target):
    p = portfolio
    response = p.client.post(
        reverse(route, args=[getattr(p, target).pk]),
        {
            'investment': p.holding.pk,
            'date': '2026-11-12',
            'amount': '100',
            'due_date': '2027-11-12',
            'notes': 'Aplicação',
        },
    )
    assert response.status_code == 302
    assert InvestmentService.get_position(p.wallet)['value'] == 900
    assert InvestmentService.get_position(p.holding)['value'] == 600


@pytest.mark.parametrize(
    'route, target',
    [
        ('redeem_investment_to_wallet', 'holding'),
        ('redeem_from_investment_transaction', 'purchase'),
    ],
)
def test_redemption_from_investment_or_purchase_records_the_wallet_credit(portfolio, route, target):
    p = portfolio
    response = p.client.post(
        reverse(route, args=[getattr(p, target).pk]),
        {
            'date': '2026-11-12',
            'amount': '100',
            'principal_amount': '100',
            'notes': 'Resgate',
        },
    )
    assert response.status_code == 302
    assert InvestmentService.get_position(p.wallet)['value'] == 1100
    assert InvestmentService.get_position(p.holding)['value'] == 400


@pytest.mark.parametrize('route', ['apply_investment_from_wallet', 'redeem_investment_to_wallet'])
def test_wallet_cannot_transfer_to_itself(portfolio, route):
    p = portfolio
    before = InvestmentTransaction.objects.count()
    assert p.client.get(reverse(route, args=[p.wallet.pk])).status_code == 302
    assert InvestmentTransaction.objects.count() == before


@pytest.mark.parametrize(
    'route, target',
    [
        ('apply_from_wallet_transaction', 'purchase'),
        ('redeem_from_investment_transaction', 'credit'),
    ],
)
def test_movement_shortcuts_reject_the_wrong_kind_of_origin(portfolio, route, target):
    p = portfolio
    assert p.client.get(reverse(route, args=[getattr(p, target).pk])).status_code == 302
    assert InvestmentTransaction.objects.count() == 2


@pytest.mark.parametrize(
    'route, target',
    [
        ('apply_investment_from_wallet', 'holding'),
        ('redeem_investment_to_wallet', 'holding'),
        ('apply_from_wallet_transaction', 'credit'),
        ('redeem_from_investment_transaction', 'purchase'),
    ],
)
def test_invalid_movement_form_preserves_money(portfolio, route, target):
    p = portfolio
    response = p.client.post(reverse(route, args=[getattr(p, target).pk]), {'amount': '-1', 'date': 'invalid'})
    assert response.status_code == 200
    assert response.context['form'].errors
    assert InvestmentTransaction.objects.count() == 2


@pytest.mark.parametrize(
    'route, target',
    [
        ('apply_investment_from_wallet', 'holding'),
        ('redeem_investment_to_wallet', 'holding'),
        ('apply_from_wallet_transaction', 'credit'),
        ('redeem_from_investment_transaction', 'purchase'),
    ],
)
def test_missing_or_inconsistent_wallet_shows_an_actionable_error(portfolio, mocker, route, target):
    mocker.patch(
        'investments.services.transaction.InvestmentTransactionService.get_or_create_default_wallet',
        side_effect=ValidationError('Caixa inconsistente'),
    )
    assert portfolio.client.get(reverse(route, args=[getattr(portfolio, target).pk])).status_code == 302


def test_domain_transfer_errors_are_shown_without_creating_movements(portfolio, mocker):
    p = portfolio
    mocker.patch(
        'investments.services.transaction.InvestmentTransactionService.transfer_between_investments',
        side_effect=ValidationError('Saldo insuficiente'),
    )
    response = p.client.post(
        reverse('apply_investment_from_wallet', args=[p.holding.pk]),
        {
            'date': '2026-11-12',
            'amount': 100,
            'due_date': '2027-11-12',
        },
    )
    assert response.status_code == 200
    assert 'Saldo insuficiente' in response.context['form'].non_field_errors()
    assert InvestmentTransaction.objects.count() == 2


def test_default_wallet_creation_is_idempotent_and_errors_are_nonfatal(authenticated_web, mocker):
    client = authenticated_web.client
    route = reverse('create_default_investment_wallet')
    assert client.get(route).status_code == 302
    assert client.post(route).status_code == 302
    assert client.post(route).status_code == 302
    assert Investment.objects.filter(default_wallet_for=authenticated_web.user).count() == 1
    mocker.patch(
        'investments.services.transaction.InvestmentTransactionService.get_or_create_default_wallet',
        side_effect=ValidationError('Caixa inconsistente'),
    )
    assert client.post(route).status_code == 302


def test_broker_crud_keeps_ownership_and_persists_edits(authenticated_web):
    client = authenticated_web.client
    assert client.post(reverse('create_broker'), {'description': 'Corretora', 'kind': 'broker'}).status_code == 302
    broker = Broker.objects.get(description='Corretora')
    assert broker.user == authenticated_web.user
    route = reverse('update_broker', args=[broker.pk])
    assert client.get(route).status_code == 200
    assert client.post(route, {'description': 'Banco', 'kind': 'bank'}).status_code == 302
    broker.refresh_from_db()
    assert broker.description == 'Banco' and broker.kind == 'bank'
    assert client.post(reverse('delete_broker', args=[broker.pk])).status_code == 302
    assert not Broker.objects.filter(pk=broker.pk).exists()


def test_broker_update_validation_error_keeps_original_record(authenticated_web, mocker):
    broker = Broker.objects.create(user=authenticated_web.user, description='Corretora')
    mocker.patch('investments.services.broker.BrokerService.update', side_effect=ValidationError('Operação rejeitada'))
    response = authenticated_web.client.post(
        reverse('update_broker', args=[broker.pk]), {'description': 'Novo nome', 'kind': 'broker'}
    )
    assert response.status_code == 200
    broker.refresh_from_db()
    assert broker.description == 'Corretora'


@pytest.mark.parametrize('value', [None, 'invalid', 'NaN', 'Infinity', '0', '-1', '.001', '1000000000000'])
def test_investment_amounts_reject_invalid_precision_and_bounds(value):
    with pytest.raises(ValidationError):
        Service.positive_amount(value)


def test_existing_unmarked_wallet_is_reused_instead_of_creating_another(portfolio):
    p = portfolio
    Investment.objects.filter(pk=p.wallet.pk).update(default_wallet_for=None)
    assert Service.get_or_create_default_wallet(p.user).pk == p.wallet.pk


def test_ambiguous_legacy_wallets_require_explicit_resolution(portfolio):
    from investments.services.transaction import DEFAULT_WALLET_INVESTMENT_DESCRIPTION

    p = portfolio
    Investment.objects.filter(pk=p.wallet.pk).update(default_wallet_for=None)
    Investment.objects.create(
        user=p.user,
        asset=p.holding.asset,
        broker=p.wallet.broker,
        description=DEFAULT_WALLET_INVESTMENT_DESCRIPTION,
        start_date=date(2020, 1, 1),
    )
    with pytest.raises(ValidationError):
        Service.get_or_create_default_wallet(p.user)


@pytest.mark.parametrize('invalid', ['same', 'closed', 'funding'])
def test_transfers_require_active_distinct_investments_and_valid_funding(portfolio, invalid):
    p = portfolio
    source, target, funding = p.wallet, p.holding, None
    if invalid == 'same':
        target = source
    elif invalid == 'closed':
        target.status = 'closed'
        target.save()
    else:
        funding = p.purchase
    before = InvestmentTransaction.objects.count()
    with pytest.raises(ValidationError):
        Service.transfer_between_investments(source, target, 100, date=date(2026, 11, 12), funding_transaction=funding)
    assert InvestmentTransaction.objects.count() == before


@pytest.mark.parametrize('invalid', ['before_credit', 'overdrawn'])
def test_funded_applications_must_respect_the_original_credit(portfolio, invalid):
    p = portfolio
    child = InvestmentTransaction.objects.create(
        user=p.user,
        investment=p.holding,
        type='aporte',
        amount=100 if invalid == 'before_credit' else 1100,
        date=date(2019, 1, 1) if invalid == 'before_credit' else date(2026, 11, 12),
        funding_transaction=p.credit,
    )
    with pytest.raises(ValidationError):
        Service.validate_funding(child)


def test_valid_funded_application_preserves_its_credit_relationship(portfolio):
    p = portfolio
    child = InvestmentTransaction.objects.create(
        user=p.user,
        investment=p.holding,
        type='aporte',
        amount=100,
        date=date(2026, 11, 12),
        funding_transaction=p.credit,
    )
    Service.validate_funding(child)
    assert child.funding_transaction == p.credit


@pytest.mark.parametrize('invalid', ['direction', 'date'])
def test_allocated_wallet_credits_cannot_change_direction_or_move_after_the_debit(portfolio, invalid):
    from bank_sync.models import CashAllocation

    p = portfolio
    debit = InvestmentTransaction.objects.create(
        user=p.user, investment=p.wallet, type='resgate', amount=100, date=date(2026, 11, 12)
    )
    CashAllocation.objects.create(credit=p.credit, debit=debit, amount=100)
    if invalid == 'direction':
        p.credit.type = 'resgate'
    else:
        p.credit.date = date(2027, 1, 1)
    with pytest.raises(ValidationError):
        Service.validate_funding(p.credit)


def test_credit_date_cannot_be_moved_after_an_existing_funded_application(portfolio):
    p = portfolio
    InvestmentTransaction.objects.create(
        user=p.user,
        investment=p.holding,
        type='aporte',
        amount=100,
        date=date(2026, 11, 12),
        funding_transaction=p.credit,
    )
    p.credit.date = date(2027, 1, 1)
    with pytest.raises(ValidationError):
        Service.validate_funding(p.credit)


def test_manual_movement_already_in_an_operation_cannot_receive_another_counterpart(portfolio):
    from uuid import uuid4

    p = portfolio
    p.purchase.operation_id = uuid4()
    p.purchase.save()
    with pytest.raises(ValidationError):
        Service.sync_manual_wallet_counterpart(p.purchase)
