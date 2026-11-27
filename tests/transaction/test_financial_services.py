from datetime import date
from types import SimpleNamespace

import pytest
from django.contrib.auth.models import AnonymousUser
from django.forms import modelform_factory
from django.utils import timezone

from login.repository import create_next_year_view
from login.services.profile import ProfileService
from statement.models import (
    CategorizationFeedback,
    Dream,
    FixedExpenses,
    Loan,
    LoanEntry,
    Notification,
    Portion,
)
from statement.services.core.categorization_feedback import CategorizationFeedbackService
from statement.services.core.fixed_expenses import FixedExpensesService
from statement.services.core.notification import NotificationService
from statement.services.core.subcategory import SubcategoryChartConfigService, SubcategoryService
from statement.services.core.transaction import TransactionService
from statement.services.dream.dream import DreamService
from statement.services.dream.portion import PortionService
from statement.services.fuel_tracking import FuelTrackingService
from statement.services.loan.loan_entry import LoanEntryService


@pytest.mark.parametrize(
    'status, method',
    [
        ('active', 'get_active_dreams'),
        ('paused', 'get_paused_dreams'),
        ('completed', 'get_completed_dreams'),
        ('cancelled', 'get_cancelled_dreams'),
    ],
)
def test_dream_status_services_scope_results_to_the_owner(ledger, status, method):
    dream = Dream.objects.create(user=ledger.user, description='Minha meta', status=status)
    Dream.objects.create(user=ledger.other, description='Meta privada', status=status)
    assert list(getattr(DreamService, method)(ledger.user)) == [dream]
    assert (dream in DreamService.get_past_dreams(ledger.user)) is (status != 'active')


def test_portion_service_sets_the_parent_and_calculates_remaining_amount(ledger):
    dream = Dream.objects.create(user=ledger.user, description='Meta', target_value=300)
    Form = modelform_factory(Portion, exclude=['user', 'dream'])
    form = Form({'description': 'Aporte', 'value': 50, 'date': '2026-11-05'})
    assert form.is_valid(), form.errors
    portion = PortionService.create(form, user=ledger.user, id=dream.pk)
    assert portion.dream == dream and portion.user == ledger.user
    assert PortionService.calculate_remaining_value(dream.pk, 300, ledger.user) == 250
    assert PortionService.calculate_remaining_value(dream.pk, 300, ledger.other) == 300


def test_loan_entry_service_assigns_the_owner_and_parent(ledger):
    loan = Loan.objects.create(user=ledger.user, description='Empréstimo')
    Form = modelform_factory(LoanEntry, exclude=['user', 'loan'])
    form = Form({'description': 'Pagamento', 'value': 50, 'date': '2026-11-05'})
    assert form.is_valid(), form.errors
    item = LoanEntryService.create(form, user=ledger.user, id=loan.pk)
    assert item.loan == loan and item.user == ledger.user
    assert list(LoanEntryService.get_by_loan(loan.pk, ledger.user)) == [item]
    assert not LoanEntryService.get_by_loan(loan.pk, ledger.other).exists()


def test_chart_configs_are_created_once_and_remain_user_scoped(ledger):
    SubcategoryService.ensure_chart_configs_for_user(ledger.user)
    SubcategoryService.ensure_chart_configs_for_user(ledger.user)
    configs = list(SubcategoryChartConfigService.get_all(ledger.user))
    assert len(configs) == 1
    config = configs[0]
    assert str(config) == f'{ledger.user} - {ledger.subcategory}'
    config.show_in_annual_statement = False
    config.save()
    assert not SubcategoryService.get_chart_config_values(ledger.user, ledger.subcategory.pk)[
        'show_in_annual_statement'
    ]
    assert SubcategoryService.get_chart_config_values(ledger.other, ledger.subcategory.pk)['show_in_annual_statement']
    SubcategoryService.ensure_chart_configs_for_user(None)
    SubcategoryService.ensure_chart_configs_for_user(AnonymousUser())
    assert SubcategoryService.get_chart_config(None, ledger.subcategory.pk) is None
    assert SubcategoryService.get_chart_config(AnonymousUser(), ledger.subcategory.pk) is None


def test_feedback_training_and_reset_operations_never_touch_other_users(ledger):
    own = CategorizationFeedback.objects.create(user=ledger.user, description='LOJA', corrected_description='Loja')
    other = CategorizationFeedback.objects.create(user=ledger.other, description='PRIVADO')
    Service = CategorizationFeedbackService
    assert list(Service.get_subcategory_untrained(ledger.user)) == [own]
    assert list(Service.get_description_untrained(ledger.user)) == [own]
    Service.set_description_training_status(own)
    Service.set_subcategory_training_status(own)
    assert not Service.get_description_untrained(ledger.user).exists()
    assert not Service.get_subcategory_untrained(ledger.user).exists()
    Service.reset_feedback(ledger.user)
    Service.reset_description_feedback(ledger.user)
    Service.reset_subcategory_feedback(ledger.user)
    own.refresh_from_db()
    assert not own.description_training and not own.subcategory_training
    Service.delete_feedbacks(ledger.user)
    assert not CategorizationFeedback.objects.filter(pk=own.pk).exists()
    assert CategorizationFeedback.objects.filter(pk=other.pk).exists()


def test_compatibility_profile_creation_is_idempotent(ledger):
    create_next_year_view(ledger.user)
    create_next_year_view(ledger.user)
    service = ProfileService(ledger.user)
    assert service.get_all().count() == 1
    assert service.get_by_id(service.configs.pk).user == ledger.user
    assert list(service.accounts) == [ledger.account]
    assert list(service.cards) == [ledger.card]


def test_fuel_configuration_can_be_created_then_cleared(ledger):
    assert FuelTrackingService.get(ledger.user) is None
    profile = FuelTrackingService.create(ledger.user, active=True, subcategory=ledger.subcategory)
    assert FuelTrackingService.get(ledger.user).subcategory == ledger.subcategory
    assert FuelTrackingService.get(ledger.user).active
    updated = FuelTrackingService.create(ledger.user, active=False)
    assert updated.pk == profile.pk
    assert not FuelTrackingService.get(ledger.user).active
    assert FuelTrackingService.get(ledger.user).subcategory is None


@pytest.mark.parametrize('created_at', [None, 'naive', 'aware'])
def test_notification_input_uses_local_civil_date(ledger, created_at):
    timestamp = None if created_at is None else timezone.datetime(2026, 11, 5, 12)
    if created_at == 'aware':
        timestamp = timezone.make_aware(timestamp)
    item = SimpleNamespace(
        pk=None, app='bank.app', title='Compra', message='Compra de R$ 25,00 em Loja.', created_at=timestamp
    )
    data = NotificationService.build_transaction_from_notification(item, ledger.user)
    assert data['posted_date'] == (timezone.localdate() if timestamp is None else date(2026, 11, 5))
    assert data['posted_date'] == data['payment_date']


def test_notification_and_transaction_first_and_order_filters(ledger, entry):
    first = entry(description='A')
    entry(description='B')
    assert TransactionService.get_by_filter(user=ledger.user, first=True) == first
    assert TransactionService.get_by_filter(first=True) == first
    assert next(iter(TransactionService.get_by_filter(order='-description'))).description == 'B'
    n = Notification.objects.create(user=ledger.user, app='app', title='Compra', message='text')
    assert NotificationService.get_by_filter(user=ledger.user, first=True) == n


def test_fixed_expense_filter_honors_owner(ledger):
    item = FixedExpenses.objects.create(user=ledger.user, description='Aluguel', start_date='2026-01-01', value=100)
    assert list(FixedExpensesService.get_by_filter(user=ledger.user)) == [item]
    assert not FixedExpensesService.get_by_filter(user=ledger.other).exists()
