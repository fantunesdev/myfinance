from types import SimpleNamespace

from statement.views.core.transaction import TransactionView


def test_update_transaction_creates_installment_when_installments_number_is_added(mocker):
    view = TransactionView()
    view._context = 'update'
    request = SimpleNamespace(user=object())
    form = object()
    instance = SimpleNamespace(installments_number=3, installment=None)
    create_mock = mocker.patch('statement.views.core.transaction.InstallmentService.create')

    view._custom_actions(request=request, form=form, instance=instance)

    create_mock.assert_called_once_with(form=form, user=request.user, transaction=instance)


def test_update_transaction_does_not_create_installment_when_already_installment(mocker):
    view = TransactionView()
    view._context = 'update'
    request = SimpleNamespace(user=object())
    form = object()
    instance = SimpleNamespace(installments_number=3, installment=object())
    create_mock = mocker.patch('statement.views.core.transaction.InstallmentService.create')

    view._custom_actions(request=request, form=form, instance=instance)

    create_mock.assert_not_called()
