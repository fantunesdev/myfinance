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


def test_dashboard_exposes_excluded_transactions_for_visibility_recalculation(mocker):
    user = object()
    instances = [
        SimpleNamespace(id=1, subcategory_id=10, user=user, type='entrada', value=5000),
        SimpleNamespace(id=2, subcategory_id=20, user=user, type='saida', value=1000, card=None, fixed=False),
        SimpleNamespace(id=3, subcategory_id=30, user=user, type='saida', value=3000, card=None, fixed=False),
    ]
    mocker.patch(
        'statement.views.core.transaction.SubcategoryService.get_chart_config_values',
        side_effect=lambda user, subcategory_id: {'show_in_monthly_cashflow_donut': subcategory_id != 30},
    )
    mocker.patch('statement.views.core.transaction.FixedExpensesService.get_active_by_date', return_value=[])

    context = TransactionView()._set_dashboard_templatetags(instances, 2026, 11)

    assert context['dashboard']['expenses'] == 1000
    assert context['dashboard']['revenue'] == 5000
    assert context['dashboard_excluded_transaction_ids'] == {3}
