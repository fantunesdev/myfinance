from datetime import date
from types import SimpleNamespace

from statement.services.core.installment import InstallmentService


def test_set_first_installment_uses_card_processing_date(mocker):
    card = SimpleNamespace(closing_day=3, expiration_day=10, prepaid=False)
    installment = object()
    transaction = SimpleNamespace(
        card=card,
        installment=None,
        paid=0,
        payment_date=date(2026, 6, 8),
        posted_date=date(2026, 6, 8),
        value=300,
        installments_number=3,
    )
    patch_mock = mocker.patch('statement.services.core.installment.InstallmentService.patch')

    InstallmentService._set_first_installment(installment, transaction)

    assert transaction.installment == installment
    assert transaction.paid == 1
    assert transaction.payment_date == date(2026, 7, 10)
    assert transaction.value == 100
    patch_mock.assert_called_once_with(
        transaction,
        {
            'value': 100,
            'paid': 1,
            'payment_date': date(2026, 7, 10),
            'installment': installment,
            'posted_date': date(2026, 6, 8),
        },
    )


def test_add_installments_does_not_mutate_first_transaction(mocker):
    transaction = SimpleNamespace(
        id=1,
        user=object(),
        paid=1,
        payment_date=date(2026, 7, 10),
        installments_number=3,
    )
    created_data = []

    def fake_model_to_dict(instance):
        return {
            'id': instance.id,
            'paid': instance.paid,
            'payment_date': instance.payment_date,
            'installments_number': instance.installments_number,
        }

    def fake_transaction_form(user, data):
        created_data.append(data)
        return SimpleNamespace()

    mocker.patch('statement.services.core.installment.model_to_dict', side_effect=fake_model_to_dict)
    mocker.patch('statement.services.core.installment.TransactionForm', side_effect=fake_transaction_form)
    create_mock = mocker.patch('statement.services.core.installment.TransactionService.create')

    InstallmentService._add_installments(transaction)

    assert transaction.paid == 1
    assert transaction.payment_date == date(2026, 7, 10)
    assert [data['paid'] for data in created_data] == [2, 3]
    assert [data['payment_date'] for data in created_data] == ['2026-08-10', '2026-09-10']
    assert create_mock.call_count == 2


def test_update_transactions_reorders_posted_dates_when_requested(mocker):
    form = SimpleNamespace(
        cleaned_data={
            'posted_date': date(2026, 6, 8),
            'reorder_posted_dates': 'True',
        }
    )
    transactions = [
        SimpleNamespace(card=None, paid=0, posted_date=None, payment_date=None),
        SimpleNamespace(card=None, paid=0, posted_date=None, payment_date=None),
        SimpleNamespace(card=None, paid=0, posted_date=None, payment_date=None),
    ]
    mocker.patch('statement.services.core.installment.InstallmentService._set_transaction_form', return_value=form)
    mocker.patch('statement.services.core.installment.TransactionService.update', side_effect=lambda form, tx: tx)

    InstallmentService._update_transactions(request=object(), form=form, transactions=transactions)

    assert [transaction.posted_date for transaction in transactions] == [
        date(2026, 6, 8),
        date(2026, 7, 8),
        date(2026, 8, 8),
    ]
    assert [transaction.paid for transaction in transactions] == [1, 2, 3]


def test_update_transactions_reorders_card_payment_dates_to_expiration_day(mocker):
    card = SimpleNamespace(expiration_day=10, prepaid=False)
    form = SimpleNamespace(
        cleaned_data={
            'posted_date': date(2026, 6, 8),
            'reorder_posted_dates': 'True',
        }
    )
    transactions = [
        SimpleNamespace(card=card, paid=0, posted_date=None, payment_date=None),
        SimpleNamespace(card=card, paid=0, posted_date=None, payment_date=None),
        SimpleNamespace(card=card, paid=0, posted_date=None, payment_date=None),
    ]
    mocker.patch('statement.services.core.installment.InstallmentService._set_transaction_form', return_value=form)
    mocker.patch('statement.services.core.installment.TransactionService.update', side_effect=lambda form, tx: tx)

    InstallmentService._update_transactions(request=object(), form=form, transactions=transactions)

    assert [transaction.posted_date for transaction in transactions] == [
        date(2026, 6, 8),
        date(2026, 7, 8),
        date(2026, 8, 8),
    ]
    assert [transaction.payment_date for transaction in transactions] == [
        date(2026, 6, 10),
        date(2026, 7, 10),
        date(2026, 8, 10),
    ]
    assert [transaction.paid for transaction in transactions] == [1, 2, 3]


def test_update_transactions_keeps_posted_dates_when_reorder_is_disabled(mocker):
    form = SimpleNamespace(
        cleaned_data={
            'posted_date': date(2026, 6, 8),
            'reorder_posted_dates': 'False',
        }
    )
    transactions = [
        SimpleNamespace(card=None, paid=0, posted_date=None, payment_date=None),
        SimpleNamespace(card=None, paid=0, posted_date=None, payment_date=None),
        SimpleNamespace(card=None, paid=0, posted_date=None, payment_date=None),
    ]
    mocker.patch('statement.services.core.installment.InstallmentService._set_transaction_form', return_value=form)
    mocker.patch('statement.services.core.installment.TransactionService.update', side_effect=lambda form, tx: tx)

    InstallmentService._update_transactions(request=object(), form=form, transactions=transactions)

    assert [transaction.posted_date for transaction in transactions] == [
        date(2026, 6, 8),
        date(2026, 6, 8),
        date(2026, 6, 8),
    ]
    assert [transaction.paid for transaction in transactions] == [1, 2, 3]
