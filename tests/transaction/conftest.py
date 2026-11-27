from datetime import date
from types import SimpleNamespace

import pytest

from login.models import User
from statement.models import (
    Account,
    AccountType,
    Bank,
    Card,
    CardNumber,
    Category,
    Currency,
    Flag,
    Subcategory,
    Transaction,
)


@pytest.fixture
def ledger(db):
    user = User.objects.create(username='ledger-owner', email='owner@ledger.invalid')
    other = User.objects.create(username='ledger-other', email='other@ledger.invalid')
    bank = Bank.objects.create(description='Bank', app_id='bank.app')
    kind = AccountType.objects.create(description='Current')
    account = Account.objects.create(user=user, bank=bank, type=kind, home_screen=True)
    other_account = Account.objects.create(user=other, bank=bank, type=kind)
    flag = Flag.objects.create(description='Flag')
    cards = [
        Card.objects.create(user=owner, account=source, flag=flag, description='Card', closing_day=3, expiration_day=10)
        for owner, source in ((user, account), (other, other_account))
    ]
    number = CardNumber.objects.create(card=cards[0], number='1234')
    category = Category.objects.create(description='Compras', type='saida')
    subcategory = Subcategory.objects.create(category=category, description='Mercado')
    currency, _ = Currency.objects.get_or_create(pk='BRL', defaults={'description': 'Real', 'symbol': 'R$'})
    return SimpleNamespace(
        user=user,
        other=other,
        account=account,
        other_account=other_account,
        card=cards[0],
        other_card=cards[1],
        number=number,
        category=category,
        subcategory=subcategory,
        currency=currency,
    )


@pytest.fixture
def entry(ledger):
    def create(**overrides):
        return Transaction.objects.create(
            **{
                'user': ledger.user,
                'account': ledger.account,
                'category': ledger.category,
                'subcategory': ledger.subcategory,
                'currency': ledger.currency,
                'description': 'Mercado',
                'original_description': 'LOJA ORIGINAL',
                'value': 25,
                'type': 'saida',
                'posted_date': date(2026, 11, 5),
                'payment_date': date(2026, 11, 5),
                **overrides,
            }
        )

    return create


@pytest.fixture
def transaction_payload(ledger):
    def payload(**overrides):
        return {
            'description': 'Mercado',
            'original_description': 'LOJA ORIGINAL',
            'value': '25.00',
            'posted_date': '2026-11-05',
            'category': ledger.category.pk,
            'subcategory': ledger.subcategory.pk,
            'account': ledger.account.pk,
            **overrides,
        }

    return payload
