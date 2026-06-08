from types import SimpleNamespace

from statement.views.core.installment import InstallmentView


def test_installment_update_form_receives_request_user(mocker):
    view = InstallmentView()
    request = SimpleNamespace(user=object(), POST={'installments_number': '3'})
    transaction = object()
    view._first_transaction = transaction
    form_mock = mocker.patch('statement.views.core.installment.InstallmentForm')

    view._set_form(request, instance=object())

    form_mock.assert_called_once_with(request.user, request.POST, instance=transaction)


def test_installment_preserve_unrendered_fields_uses_first_transaction(mocker):
    class FakeTransaction:
        objects = mocker.Mock()

    view = InstallmentView()
    original_transaction = object()
    FakeTransaction.objects.get.return_value = original_transaction
    view._first_transaction = FakeTransaction()
    view._first_transaction.pk = 10
    form = object()
    preserve_mock = mocker.patch('statement.views.base_view.BaseView._preserve_unrendered_fields_after_validation')

    view._preserve_unrendered_fields_after_validation(form=form, original_instance=object())

    FakeTransaction.objects.get.assert_called_once_with(pk=10)
    preserve_mock.assert_called_once_with(form, original_transaction)


def test_installment_update_custom_actions_uses_transaction_installment_id(mocker):
    view = InstallmentView()
    view._context = 'update'
    request = SimpleNamespace(user=object())
    form = object()
    transaction = SimpleNamespace(id=999, installment_id=153)
    transactions = object()
    get_transactions_mock = mocker.patch.object(view, '_get_transactions', return_value=transactions)
    update_plan_mock = mocker.patch('statement.views.core.installment.InstallmentService.update_installment_plan')

    view._custom_actions(request=request, form=form, instance=transaction)

    get_transactions_mock.assert_called_once_with(request, 153)
    update_plan_mock.assert_called_once_with(request, form, transactions)


def test_installment_update_does_not_call_generic_service_update(mocker):
    view = InstallmentView()
    request = SimpleNamespace(user=SimpleNamespace(is_authenticated=True), POST={})
    installment = object()
    transaction = object()
    form = SimpleNamespace(is_valid=lambda: True, instance=transaction)
    view.service = mocker.Mock()
    view.service.get_by_id.return_value = installment
    get_transaction_mock = mocker.patch.object(view, '_get_transaction', return_value=transaction)
    mocker.patch.object(view, '_set_form', return_value=form)
    preserve_mock = mocker.patch.object(view, '_preserve_unrendered_fields_after_validation')
    custom_actions_mock = mocker.patch.object(view, '_custom_actions')
    redirect_mock = mocker.patch('statement.views.core.installment.redirect', return_value='redirected')

    response = view.update(request, id=153)

    assert response == 'redirected'
    get_transaction_mock.assert_called_once_with(request, 153)
    preserve_mock.assert_called_once_with(form, transaction)
    custom_actions_mock.assert_called_once_with(request=request, form=form, instance=transaction)
    view.service.update.assert_not_called()
    redirect_mock.assert_called_once_with(view.redirect_url)
