from datetime import date
from types import SimpleNamespace
from uuid import uuid4

import pytest
from django.utils import timezone

from bank_sync.models import (
    BankConnection,
    ExternalInvestment,
    InvestmentCashEvidence,
    InvestmentEvent,
    InvestmentHistoryJob,
)
from investments.models import Asset, Broker, Investment, InvestmentTransaction
from investments.services.transaction import InvestmentTransactionService
from login.models import User


@pytest.fixture
def registered_bank_trade(bank_case):
    from bank_sync.bank_trades import register_purchase
    from bank_sync.investment_events import reconcile

    b = bank_case
    b.movement.delete()
    b.counterpart.delete()
    InvestmentTransaction.objects.create(
        user=b.user, investment=b.investment, type='aporte', amount=100, quantity=10, date=date(2020, 1, 1)
    )
    b.event.facts.update(amount=110, netAmount=110, quantity=10)
    b.event.save()
    b.cash.facts['amount'] = 110
    b.cash.save()
    b.sale = reconcile(
        b.user, b.event.pk, 1, 'apply', principal=100, cash_ids=[b.cash.pk], evidence='Resgate documentado'
    )
    b.debit = InvestmentCashEvidence.objects.create(
        connection=b.connection,
        external_id=str(uuid4()),
        account_id=b.cash.account_id,
        facts={
            'type': 'DEBIT',
            'amount': -110,
            'date': '2026-11-12T00:01:00Z',
            'description': 'Compra - Criptomoedas',
            'status': 'POSTED',
            'currencyCode': 'BRL',
        },
    )
    b.trade = register_purchase(b.user, b.debit.pk, 1, b.source.pk, b.cash.pk, 'BTC', '.01', 'Compra documentada')
    b.crypto_source = ExternalInvestment.objects.create(
        connection=b.connection, external_id=uuid4(), facts={'name': 'Bitcoin', 'type': 'CRYPTO', 'currencyCode': 'BRL'}
    )
    b.crypto_event = InvestmentEvent.objects.create(
        connection=b.connection,
        external_id=str(uuid4()),
        last_seen_job=b.job,
        facts={
            'type': 'BUY',
            'quantity': '.01',
            'amount': 110,
            'netAmount': 110,
            'date': '2026-11-12T00:00:00Z',
        },
    )
    b.crypto_event.investments.add(b.crypto_source)
    return b


@pytest.fixture
def bank_case(db):
    user = User.objects.create(username='bank-guards', email='guards@bank.invalid')
    connection = BankConnection.objects.create(user=user, item_id=uuid4())
    wallet = InvestmentTransactionService.get_or_create_default_wallet(user)
    broker = Broker.objects.create(user=user, description='Inter', kind='bank')
    asset = Asset.objects.create(user=user, description='LCI', symbol='LCI', asset_type='fixed_income')
    investment = Investment.objects.create(
        user=user, asset=asset, broker=broker, description='Inter LCI', start_date=date(2026, 1, 1)
    )
    source = ExternalInvestment.objects.create(
        connection=connection, external_id=uuid4(), investment=investment, facts={'name': 'LCI', 'currencyCode': 'BRL'}
    )
    job = InvestmentHistoryJob.objects.create(connection=connection, state='succeeded', finished_at=timezone.now())
    event = InvestmentEvent.objects.create(
        connection=connection,
        external_id=str(uuid4()),
        last_seen_job=job,
        facts={
            'type': 'SELL',
            'date': '2026-11-12T00:00:00Z',
            'netAmount': 100,
            'amount': 101,
            'quantity': 10,
        },
    )
    event.investments.add(source)
    operation = uuid4()
    movement = InvestmentTransaction.objects.create(
        user=user,
        investment=investment,
        date=date(2026, 11, 12),
        type='resgate',
        amount=100,
        quantity=10,
        operation_id=operation,
    )
    counterpart = InvestmentTransaction.objects.create(
        user=user, investment=wallet, date=date(2026, 11, 12), type='aporte', amount=100, operation_id=operation
    )
    cash = InvestmentCashEvidence.objects.create(
        connection=connection,
        external_id=str(uuid4()),
        account_id=uuid4(),
        facts={
            'type': 'CREDIT',
            'date': '2026-11-12T00:00:00Z',
            'amount': 100,
            'description': 'Resgate - LCI Inter',
            'status': 'POSTED',
            'currencyCode': 'BRL',
        },
    )
    return SimpleNamespace(
        user=user,
        connection=connection,
        wallet=wallet,
        broker=broker,
        asset=asset,
        investment=investment,
        source=source,
        job=job,
        event=event,
        movement=movement,
        counterpart=counterpart,
        cash=cash,
    )
