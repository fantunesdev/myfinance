from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.utils import translation

from login.models import User
from statement.models import Dream
from statement.templatetags import custom_filters as filters
from statement.templatetags import custom_tags as tags
from statement.utils.utils import DictToObject


@pytest.mark.parametrize('value, expected', [(None, 'R$ 0,00'), ('bad', 'R$ 0,00'), (1234.5, 'R$ 1.234,50')])
def test_currency_filters_handle_missing_invalid_and_numeric_amounts(value, expected):
    assert filters.to_reais(value) == expected
    assert filters.to_currency(value, 'R$') == expected


@pytest.mark.parametrize(
    'value, expected', [(None, ''), ('', ''), ('bad', 'bad'), ('10.000', '10'), ('1.2500', '1,25'), (0, '0')]
)
def test_quantity_formatting_keeps_significant_digits(value, expected):
    assert filters.format_quantity(value) == expected


@pytest.mark.parametrize('value, expected', [(True, 'Sim'), (False, 'Não')])
def test_boolean_labels(value, expected):
    assert filters.bool_to_portuguese(value) == filters.handle_boolean(value) == expected


def test_image_and_optional_field_rendering():
    assert filters.handle_image(SimpleNamespace(url='/media/photo.jpg')) == '/media/photo.jpg'
    assert filters.handle_image(None) == ''
    assert filters.handle_none(None) == ''
    assert filters.handle_none('text') == 'text'
    assert tags.capitalize_first('EXEMPLO') == 'Exemplo'
    assert tags.capitalize_first(42) == 42


@pytest.mark.parametrize('count, expected', [(0, 'Compra'), (3, 'Compra (2/3)')])
def test_installment_label(count, expected):
    assert (
        filters.paid_installments(SimpleNamespace(installments_number=count, paid=2, description='Compra')) == expected
    )


def test_transaction_totals_use_the_currency_symbol():
    currency = SimpleNamespace(symbol='€')
    rows = [SimpleNamespace(value=Decimal('12.50'), currency=currency), SimpleNamespace(value=Decimal('7.50'))]
    assert filters.total_amount(rows) == '€ 20,00'


def test_detail_fields_include_properties_and_annotations_and_hide_private_state():
    dream = Dream(description='Viagem', target_value=100, user=User(username='unsaved'))
    dream.extra = 'annotation'
    dream._private = 'secret'
    dream.hidden_detail_fields = ('notes', 'hidden_detail_fields')
    values = dict(filters.get_fields(dream))
    assert values['description'] == 'Viagem'
    assert values['extra'] == 'annotation'
    assert values['current_value'] == 0
    assert values['remaining_value'] == 100
    assert values['progress_percentage'] == 0
    assert '_private' not in values and 'notes' not in values
    assert filters.get_field_value(dream, 'extra') == 'annotation'
    assert filters.get_field_value(dream, 'missing') == ''


@pytest.fixture
def calendar(mocker):
    frozen = mocker.patch('statement.templatetags.custom_tags.date')
    frozen.today.return_value = date(2026, 11, 10)


@pytest.mark.parametrize(
    'deadline, months, monthly',
    [
        (None, 0, 1200),
        (date(2026, 10, 1), 0, 1200),
        (date(2026, 11, 20), 0, 1200),
        (date(2027, 1, 1), 2, 600),
    ],
)
def test_dream_monthly_amount_handles_missing_expired_same_month_and_year_rollover(calendar, deadline, months, monthly):
    dream = Dream(target_value=1200, limit_date=deadline)
    assert tags.calculate_remaining_months(dream) == months
    assert tags._calculate_remaining_installment_value(dream) == monthly


@pytest.mark.django_db
def test_dream_template_tags_scope_totals_to_the_user(calendar):
    owner = User.objects.create(username='dream-tag', email='tag@test.invalid')
    other = User.objects.create(username='other-tag', email='other-tag@test.invalid')
    dream = Dream.objects.create(user=owner, description='Viagem', target_value=1200, limit_date=date(2027, 1, 1))
    with translation.override('pt-br'):
        assert tags.get_cumulative_total_for_dream(dream.pk, owner) == 'R$ 0,00'
        assert tags.get_cumulative_total_for_dream(dream.pk, other) == 'R$ 0,00'
        assert tags.get_remaining_value_for_dream(dream.pk, 100, owner) == 'R$ 1.200,00'
        assert tags.get_remaining_value_for_dream(dream.pk, 100, other) == 'R$ 100,00'
        assert tags.calcule_remaining_installment_value(dream.pk, 100, None, owner) == 'R$ 600,00'
        assert tags.calcule_remaining_installment_value(999999, 100, None, owner) == 'R$ 100,00'
        assert tags.total_remaining_installment_value_for_dreams([dream]) == 'R$ 600,00'
        assert tags.total_remaining_installment_value_for_dreams([]) == 'R$ 0,00'


def test_dictionary_object_preserves_attributes_and_readable_representation():
    data = {'amount': 10, 'description': 'Compra'}
    obj = DictToObject(data)
    assert obj.amount == 10 and obj.description == 'Compra'
    assert str(obj) == str(data) and repr(obj) == repr(data)
