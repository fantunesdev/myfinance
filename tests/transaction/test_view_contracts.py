from types import SimpleNamespace

import pytest
from django.test import RequestFactory

from api.views.account import AccountView
from investments.views.base import InvestmentCrudView
from statement.forms.core.transaction import TransactionForm
from statement.models import Transaction
from statement.services.core.transaction import TransactionService
from statement.utils.datetime import DateTimeUtils
from statement.views.base_view import BaseView
from statement.views.core.notification import NotificationView
from statement.views.core.transaction import TransactionView
from statement.views.device import DeviceView
from statement.views.loan.loan_entry import LoanEntryView


@pytest.mark.parametrize('view_type', [BaseView, InvestmentCrudView, TransactionView, LoanEntryView])
def test_form_builders_reject_an_undefined_operation_context(ledger, view_type):
    view = view_type()
    request = RequestFactory().get('/form/')
    request.user = ledger.user
    with pytest.raises(ValueError, match='contexto'):
        view._set_form(request, None)


@pytest.mark.parametrize('model', [Transaction, None, object()])
def test_generic_lists_handle_forms_requiring_a_user_and_unavailable_model_metadata(ledger, mocker, model):
    view = BaseView()
    view.class_has_user = True
    view.service = TransactionService
    view.class_form = TransactionForm
    view.model = model
    view._render = mocker.Mock(side_effect=lambda request, form, template, context: context)
    request = RequestFactory().get('/list/')
    request.user = ledger.user
    context = view.get_all(request)
    assert ('description' in context['fields']) is (model is Transaction)


def test_notification_list_subclasses_can_omit_the_owner_column(ledger, mocker):
    view = NotificationView()
    view._context = 'get_all'
    view.list_fields = ['app', 'title']
    view.column_names = ['Aplicação', 'Título']
    mocker.patch(
        'statement.views.core.notification.NotificationTitleService.ensure_titles',
        side_effect=RuntimeError('unavailable'),
    )
    context = view._add_context_on_templatetags(SimpleNamespace(user=ledger.user), [])
    assert context['column_names'] == ['Aplicação', 'Título']
    assert context['notification_titles'] == []


def test_device_deletion_context_does_not_query_the_device_list(ledger):
    view = DeviceView()
    view._context = 'delete'
    assert view._add_context_on_templatetags(SimpleNamespace(user=ledger.user), None) == {}


@pytest.mark.parametrize('many', [True, False])
def test_generic_api_serialization_supports_single_objects_and_sequences(ledger, many):
    view = AccountView()
    response = view._serialize_and_return([ledger.account] if many else ledger.account)
    data = response.data[0] if many else response.data
    assert response.status_code == 200
    assert data['id'] == ledger.account.pk


def test_unsupported_month_arithmetic_input_has_no_date_result():
    assert DateTimeUtils.add_months(None, 1) is None
