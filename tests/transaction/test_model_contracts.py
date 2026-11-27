from datetime import date

import pytest
from django.forms import modelform_factory

from api.serializers.base_serializer import BaseSerializer
from login.models import Profile
from login.services.profile import ProfileService
from statement.entities.transaction import Transaction as TransactionData
from statement.models import (
    CSVImportConfig,
    Dream,
    FixedExpenses,
    Loan,
    LoanEntry,
    Notification,
    NotificationTitle,
    NotificationTitlePreference,
)


def test_transaction_data_preserves_all_values_and_has_a_readable_representation():
    fields = {
        'posted_date': date(2026, 11, 5),
        'payment_date': date(2026, 11, 5),
        'account': 1,
        'card': None,
        'category': 2,
        'subcategory': 3,
        'description': 'Compra',
        'value': 100,
        'installments_number': 0,
        'paid': 0,
        'fixed': False,
        'annual': False,
        'currency': 'BRL',
        'observation': '',
        'remember': False,
        'type': 'saida',
        'effected': True,
        'home_screen': True,
        'user': 1,
        'installment': None,
    }
    obj = TransactionData(**fields)
    assert obj.to_dict() == fields
    assert str(obj) == 'Compra'
    assert 'description: Compra' in repr(obj)
    assert obj.set_payment_date() == date(2026, 11, 5)


def test_transaction_data_resolves_the_selected_card(ledger):
    data = {name: None for name in TransactionData.__init__.__code__.co_varnames[1:21]}
    data.update(card=ledger.card.pk, description='Compra')
    obj = TransactionData(**data)
    assert obj.set_payment_date() is None
    assert obj.card == ledger.card


def test_profile_service_create_update_and_delete(ledger):
    service = ProfileService(ledger.user)
    Form = modelform_factory(Profile, fields=['use_next_month', 'next_month_day'])
    profile = service.create(Form({'use_next_month': True, 'next_month_day': 20}))
    assert profile.user == ledger.user
    assert profile.use_next_month
    updated = service.update(Form({'use_next_month': False, 'next_month_day': 10}, instance=profile), profile)
    assert not updated.use_next_month and updated.next_month_day == 10
    service.delete(updated)
    assert not Profile.objects.filter(user=ledger.user).exists()


def test_dream_progress_handles_an_unfunded_or_overfunded_target(ledger, entry):
    assert Dream(target_value=0).progress_percentage == 0
    dream = Dream.objects.create(user=ledger.user, description='Meta', target_value=100)
    entry(dream=dream, value=120)
    assert dream.current_value == 120
    assert dream.remaining_value == 0
    assert dream.progress_percentage == 100


def test_human_readable_financial_model_labels(ledger):
    dream = Dream(description='Meta')
    loan = Loan(description='Empréstimo')
    movement = LoanEntry(description='Pagamento')
    fixed = FixedExpenses(description='Aluguel')
    assert str(dream) == 'Meta' and str(loan) == 'Empréstimo' and str(movement) == 'Pagamento'
    assert str(fixed) == 'Aluguel'
    assert str(ledger.account.type) == 'Current'
    assert str(ledger.number) == '1234'
    assert ledger.card.all_card_numbers
    config = CSVImportConfig(name='Importação')
    assert str(config) == 'Importação'
    notification = Notification(app='app', title='Compra', message='Mensagem')
    assert str(notification) == 'app - Compra - Mensagem'
    title = NotificationTitle(title='Compra')
    preference = NotificationTitlePreference(user=ledger.user, title=title)
    assert str(title) and str(preference)


def test_serializer_subclasses_must_specify_their_model():
    class MissingModelSerializer(BaseSerializer):
        class Meta:
            fields = '__all__'

    with pytest.raises(ValueError, match='model'):
        MissingModelSerializer()


def test_legacy_subcategory_module_remains_importable():
    from api.views.subcategoy import SubcategoryView
    from statement.services.core.subcategory import SubcategoryService

    assert SubcategoryView.service is SubcategoryService
