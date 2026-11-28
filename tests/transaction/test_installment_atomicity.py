from types import SimpleNamespace

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.forms.models import model_to_dict
from django.urls import reverse
from rest_framework.test import APIClient

from investments.models import Asset, Broker, Investment, InvestmentTransaction
from statement.forms.core.installment import InstallmentForm
from statement.models import FuelEntry, Installment, Transaction
from statement.services.core.installment import InstallmentService
from statement.services.core.transaction import TransactionService


def financial_state():
    return {
        model._meta.label: list(model.objects.order_by('pk').values())
        for model in (Installment, Transaction, FuelEntry, Asset, Broker, Investment, InvestmentTransaction)
    }


def fail_after_write(mocker, method, ordinal, error):
    original = getattr(TransactionService, method)
    calls = 0

    def write(*args, **kwargs):
        nonlocal calls
        result = original(*args, **kwargs)
        calls += 1
        if calls == ordinal:
            raise error('Falha intermediária no parcelamento')
        return result

    return mocker.patch.object(TransactionService, method, side_effect=write)


@pytest.fixture
def installment_client(authenticated_web, ledger):
    authenticated_web.client.force_login(ledger.user)
    return authenticated_web.client


def plan_payload(ledger, **overrides):
    return {
        'description': 'Compra parcelada',
        'type': 'saida',
        'value': '90',
        'posted_date': '2026-11-05',
        'payment_date': '2026-12-10',
        'category': ledger.category.pk,
        'subcategory': ledger.subcategory.pk,
        'account': '',
        'card': ledger.card.pk,
        'currency': 'BRL',
        'installments_number': 3,
        'paid': 0,
        'payment_method': 1,
        **overrides,
    }


@pytest.fixture
def manual_plan(ledger, entry):
    first = entry(
        account=None,
        card=ledger.card,
        value=90,
        installments_number=3,
        home_screen=ledger.card.home_screen,
        observation='',
    )
    plan = InstallmentService.create(None, user=ledger.user, transaction=first)
    # A failed plan operation must also leave unrelated financial records alone.
    entry(user=ledger.other, account=ledger.other_account, description='Outro usuário')
    return plan


@pytest.mark.parametrize('error', [RuntimeError, ValidationError, IntegrityError])
def test_service_creation_restores_existing_first_transaction_on_failure(ledger, entry, mocker, error):
    first = entry(account=None, card=ledger.card, value=90, installments_number=3)
    before = financial_state()
    write = fail_after_write(mocker, 'create', 2, error)

    with pytest.raises(error, match='Falha intermediária'):
        InstallmentService.create(None, user=ledger.user, transaction=first)

    assert write.call_count == 2
    assert financial_state() == before


@pytest.mark.parametrize('endpoint', ['api', 'web_create', 'web_convert'])
@pytest.mark.parametrize('error', [RuntimeError, ValidationError, IntegrityError])
@pytest.mark.parametrize('investment_backed', [False, True])
def test_creation_entry_points_roll_back_the_entire_plan(
    installment_client,
    ledger,
    entry,
    mocker,
    endpoint,
    error,
    investment_backed,
    django_capture_on_commit_callbacks,
):
    ledger.subcategory.is_investment = investment_backed
    ledger.subcategory.save()
    if endpoint == 'web_convert':
        first = entry(description='Lançamento original', value=90)
    entry(user=ledger.other, account=ledger.other_account, description='Outro usuário')
    before = financial_state()
    # Creating through HTTP also saves the original purchase; conversion reuses it.
    write = fail_after_write(mocker, 'create', 2 if endpoint == 'web_convert' else 3, error)

    def submit():
        if endpoint == 'api':
            data = plan_payload(ledger, description='Compra parcelada 1/3', installment_value_mode='total')
            client = APIClient()
            client.force_authenticate(user=ledger.user)
            return client.post(reverse('transactions-list'), data, format='json')
        if endpoint == 'web_create':
            return installment_client.post(reverse('create_transaction', args=['saida']), plan_payload(ledger))
        return installment_client.post(
            reverse('update_transaction', args=[first.pk]),
            plan_payload(ledger, installment_option='parcelar'),
        )

    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        if error is ValidationError and endpoint != 'api':
            response = submit()
            assert response.status_code == 200
            assert 'Falha intermediária no parcelamento' in response.context['form'].non_field_errors()
        else:
            with pytest.raises(error, match='Falha intermediária'):
                submit()

    assert write.call_count == (2 if endpoint == 'web_convert' else 3)
    assert financial_state() == before
    assert callbacks == []


@pytest.mark.parametrize('endpoint', ['service', 'web'])
@pytest.mark.parametrize(
    'new_count, method, ordinal', [(3, 'update', 2), (4, 'create', 1), (2, 'update', 1), (1, 'delete', 2)]
)
@pytest.mark.parametrize('error', [RuntimeError, ValidationError, IntegrityError])
def test_manual_plan_edit_rolls_back_updates_additions_and_deletions(
    manual_plan, installment_client, ledger, mocker, endpoint, new_count, method, ordinal, error
):
    before = financial_state()
    payload = plan_payload(
        ledger,
        description='Descrição alterada',
        value='40',
        installments_number=new_count,
        paid=1,
        reorder_posted_dates='False',
    )
    rows = Transaction.objects.filter(installment=manual_plan).order_by('paid', 'pk')
    form = InstallmentForm(ledger.user, data=payload, instance=rows.first())
    assert form.is_valid(), form.errors
    write = fail_after_write(mocker, method, ordinal, error)

    def submit():
        if endpoint == 'service':
            return InstallmentService.update_installment_plan(SimpleNamespace(user=ledger.user), form, rows)
        return installment_client.post(reverse('update_installment', args=[manual_plan.pk]), payload)

    if error is ValidationError and endpoint == 'web':
        response = submit()
        assert response.status_code == 200
        assert 'Falha intermediária no parcelamento' in response.context['form'].non_field_errors()
    else:
        with pytest.raises(error, match='Falha intermediária'):
            submit()

    assert write.call_count == ordinal
    assert financial_state() == before


@pytest.mark.parametrize('source_type', ['pluggy', 'pluggy_projection'])
@pytest.mark.parametrize('fail', [False, True])
def test_received_plan_keeps_individual_amounts_dates_and_provenance(
    manual_plan, installment_client, ledger, mocker, source_type, fail
):
    rows = Transaction.objects.filter(installment=manual_plan).order_by('paid', 'pk')
    amounts = [30.02, 29.99, 29.99]
    for row, amount in zip(rows, amounts, strict=True):
        row.value = amount
        row.source_type = source_type
        row.source_app = 'bank.app'
        row.save()
    before = financial_state()
    anchor = rows.first()
    payload = model_to_dict(anchor)
    payload.update(description='Revisado', reorder_posted_dates='False')
    payload = {key: '' if value is None else value for key, value in payload.items()}
    if fail:
        write = fail_after_write(mocker, 'update', 2, ValidationError)

    response = installment_client.post(reverse('update_installment', args=[manual_plan.pk]), payload)

    if fail:
        assert response.status_code == 200
        assert 'Falha intermediária no parcelamento' in response.context['form'].non_field_errors()
        assert write.call_count == 2
        assert financial_state() == before
    else:
        assert response.status_code == 302
        after = financial_state()
        for row in before[Transaction._meta.label]:
            if row['installment_id'] == manual_plan.pk:
                row['description'] = 'Revisado'
        assert after == before


def fail_with_duplicate_plan(mocker, method, ordinal):
    original = getattr(TransactionService, method)
    calls = 0

    def write(*args, **kwargs):
        nonlocal calls
        result = original(*args, **kwargs)
        calls += 1
        if calls == ordinal:
            plan = Installment.objects.get(pk=result.installment_id)
            # Exercise an actual database error, including Django's broken-transaction state.
            Installment.objects.create(
                pk=plan.pk, user=plan.user, description=plan.description, posted_date=plan.posted_date
            )
        return result

    return mocker.patch.object(TransactionService, method, side_effect=write)


@pytest.mark.parametrize('endpoint', ['service', 'api', 'web'])
def test_creation_rolls_back_after_a_real_database_constraint_failure(
    installment_client, ledger, entry, mocker, endpoint
):
    if endpoint == 'service':
        first = entry(account=None, card=ledger.card, value=90, installments_number=3)
    before = financial_state()
    ordinal = 2 if endpoint == 'service' else 3
    write = fail_with_duplicate_plan(mocker, 'create', ordinal)

    with pytest.raises(IntegrityError):
        if endpoint == 'service':
            InstallmentService.create(None, user=ledger.user, transaction=first)
        elif endpoint == 'api':
            client = APIClient()
            client.force_authenticate(user=ledger.user)
            client.post(
                reverse('transactions-list'),
                plan_payload(ledger, description='Compra parcelada 1/3', installment_value_mode='total'),
                format='json',
            )
        else:
            installment_client.post(reverse('create_transaction', args=['saida']), plan_payload(ledger))

    assert write.call_count == ordinal
    assert financial_state() == before


@pytest.mark.parametrize('new_count, method', [(2, 'update'), (3, 'update'), (4, 'create')])
def test_edit_restores_the_plan_after_a_real_database_constraint_failure(
    manual_plan, installment_client, ledger, mocker, new_count, method
):
    before = financial_state()
    write = fail_with_duplicate_plan(mocker, method, 1 if new_count != 3 else 2)

    with pytest.raises(IntegrityError):
        installment_client.post(
            reverse('update_installment', args=[manual_plan.pk]),
            plan_payload(
                ledger,
                description='Revisado',
                value=40,
                installments_number=new_count,
                paid=1,
                reorder_posted_dates='False',
            ),
        )

    assert write.call_count == (1 if new_count != 3 else 2)
    assert financial_state() == before
