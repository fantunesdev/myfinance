from datetime import date
from decimal import Decimal
from importlib import import_module
from types import SimpleNamespace

import pytest
from django.apps import apps
from django.forms import model_to_dict
from django.db import connection

from login.models import Profile, User
from statement.forms.core.transaction import TransactionForm, TransactionExpenseForm
from statement.models import Category, Currency, FuelEntry, Subcategory, Transaction
from statement.services.core.transaction import TransactionService
from statement.services.core.installment import InstallmentService
from statement.services.fuel_entries import fuel_history, summarize_fuel
from statement.views.core.transaction import TransactionView


def point(day, odometer, liters=40, full=True, broken=False, amount=None, currency='BRL'):
    return {
        'id': day, 'date': date(2026, 1, day).isoformat(),
        'odometer': Decimal(str(odometer)) if odometer is not None else None,
        'liters': Decimal(str(liters)) if liters else None,
        'amount': Decimal(str(amount if amount is not None else (liters or 0) * 6)),
        'currency': currency, 'full_tank': full, 'break_before': broken,
        'category_id': 1, 'subcategory_id': 2,
    }


def test_partials_are_included_and_initial_fill_is_excluded():
    report = summarize_fuel([point(1, 82000), point(2, 82300, 20, False), point(3, 82800, 30)])
    assert report['consumption'] == 16
    assert report['distance'] == 800
    assert report['liters'] == 50
    assert report['cost_per_km'] == Decimal('0.375')
    assert report['periods'][0]['refuelings'] == 2


def test_continuous_history_grows_one_period_without_overlap():
    report = summarize_fuel([point(1, 1000), point(2, 1400), point(3, 1800)])
    assert len(report['periods']) == 1
    assert report['distance'] == 800
    assert report['liters'] == 80
    assert report['consumption'] == 10


def test_separate_periods_use_weighted_average():
    report = summarize_fuel([
        point(1, 1000), point(2, 2000, 100),
        point(3, 2500, broken=True), point(4, 5500, 200),
    ])
    assert len(report['periods']) == 2
    assert report['consumption'] == Decimal(4000) / Decimal(300)
    assert report['days'] == 2


def test_gap_discards_open_interval_and_restarts_at_next_full_reading():
    report = summarize_fuel([
        point(1, 1000), point(2, 1200, 20, False),
        point(3, 1400, 20, False, True), point(4, 1800), point(5, 2200),
    ])
    assert report['distance'] == 400
    assert report['liters'] == 40
    assert len(report['excluded']) == 2


def test_missing_middle_odometer_is_allowed_when_liters_are_known():
    report = summarize_fuel([point(1, 1000), point(2, None, 10, False), point(3, 1500, 40)])
    assert report['consumption'] == 10


def test_unknown_tank_is_not_an_anchor_and_partial_tail_remains_pending():
    report = summarize_fuel([point(1, 1000, full=None), point(2, 1500), point(3, 1700, 20, False)])
    assert report['consumption'] is None
    assert len(report['excluded']) == 1
    assert len(report['pending']) == 1


@pytest.mark.parametrize('middle', [point(2, 1500, None, False), point(2, 1900, 20, False)])
def test_invalid_or_missing_intermediate_data_never_produces_a_valid_average(middle):
    report = summarize_fuel([point(1, 1000), middle, point(3, 1800)])
    assert report['consumption'] is None


def test_mixed_currencies_keep_consumption_but_do_not_mix_money():
    report = summarize_fuel([point(1, 1000), point(2, 1100, 10, False), point(3, 1500, 40, currency='USD')])
    assert report['consumption'] == 10
    assert report['cost_per_km'] is None
    assert report['price_per_liter'] is None


def test_first_full_tank_keeps_individual_consumption_out_of_historical_average():
    entry = {**point(1, 83252, 36), 'distance': Decimal('450')}
    report = summarize_fuel([entry])
    assert report['consumption'] is None
    assert report['distance'] == 0
    assert report['liters'] == 0
    assert report['periods'] == []
    individual = FuelEntry(liters=Decimal('36'), distance_km=Decimal('450'), amount_paid=Decimal('230'))
    assert individual.consumption == Decimal('12.5')


def test_direct_distance_without_odometer_does_not_start_historical_average():
    report = summarize_fuel([{**point(1, None, 36), 'distance': Decimal('450')}])
    assert report['consumption'] is None
    assert report['periods'] == []


def test_partial_with_direct_distance_is_not_used_for_overall_average():
    report = summarize_fuel([{**point(1, 83252, 36, False), 'distance': Decimal('450')}])
    assert report['consumption'] is None


def test_historical_average_waits_for_closed_odometer_interval_despite_direct_distance():
    history = [point(1, 1000), {**point(2, None, 20), 'distance': Decimal('200')}]
    assert summarize_fuel(history)['consumption'] is None
    report = summarize_fuel([*history, point(3, 1500, 30)])
    assert report['distance'] == 500
    assert report['liters'] == 50
    assert len(report['periods']) == 1
    assert report['periods'][0]['source'] == 'odometer'


@pytest.mark.parametrize('distance', [None, Decimal('200'), Decimal('9999')])
def test_informed_distances_never_change_odometer_average(distance):
    report = summarize_fuel([
        {**point(1, 1000, 20), 'distance': distance},
        {**point(2, 1600, 40), 'distance': distance},
    ])
    assert report['distance'] == 600
    assert report['liters'] == 40
    assert report['consumption'] == 15
    assert len(report['periods']) == 1


@pytest.fixture
def fuel(db):
    user = User.objects.create(username='fuel', email='fuel@test.invalid')
    category = Category.objects.create(description='Transporte', type='saida')
    subcategory = Subcategory.objects.create(description='Combustível', category=category)
    currency, _ = Currency.objects.get_or_create(pk='BRL', defaults={'description': 'Real', 'symbol': 'R$'})
    Profile.objects.create(user=user, enable_fuel_tracking=True, fuel_subcategory=subcategory)
    transaction = Transaction.objects.create(
        user=user, category=category, subcategory=subcategory, currency=currency,
        posted_date=date(2026, 1, 1), payment_date=date(2026, 2, 10),
        value=240, description='Posto', type='saida', observation='Meu comentário',
    )
    return SimpleNamespace(**locals())


def data_for(transaction, **extra):
    return {
        **model_to_dict(transaction), 'fuel_tracking_present': 'on', 'fuel_liters': '40',
        'fuel_odometer_km': '1000', 'fuel_full_tank': 'True', **extra,
    }


def test_form_and_service_store_facts_and_leave_comment_untouched(fuel):
    form = TransactionForm(fuel.user, data_for(fuel.transaction, value='220', fuel_distance_km='400'), instance=fuel.transaction)
    assert form.is_valid(), form.errors
    TransactionService.update(form, fuel.transaction)
    entry = FuelEntry.objects.get(transaction=fuel.transaction)
    assert entry.price_per_liter == Decimal('5.5')
    assert entry.consumption == 10
    assert entry.cost_per_km == Decimal('0.55')
    assert entry.transaction.observation == 'Meu comentário'
    edit = TransactionForm(fuel.user, instance=entry.transaction)
    assert edit['fuel_odometer_km'].value() == 1000
    assert edit['fuel_full_tank'].value() == 'True'


def test_update_view_preserves_only_model_fields_not_optional_fuel_fields(fuel):
    original = Transaction.objects.get(pk=fuel.transaction.pk)
    form = TransactionForm(fuel.user, data_for(fuel.transaction), instance=fuel.transaction)
    assert form.is_valid(), form.errors
    TransactionView()._preserve_unrendered_fields_after_validation(form, original)
    assert not hasattr(form.instance, 'fuel_amount_paid')


def test_fuel_subcategory_is_configured_instead_of_hardcoded(fuel):
    assert TransactionForm(fuel.user).fuel_subcategory_id == fuel.subcategory.pk


def test_price_and_total_calculate_liters_without_javascript(fuel):
    form = TransactionForm(fuel.user, data_for(
        fuel.transaction, value='10', fuel_liters='', fuel_price_per_liter='6.4',
    ), instance=fuel.transaction)
    assert form.is_valid(), form.errors
    TransactionService.update(form, fuel.transaction)
    entry = FuelEntry.objects.get(transaction=fuel.transaction)
    assert entry.liters == Decimal('1.563')
    assert entry.informed_price_per_liter == Decimal('6.4')
    assert entry.price_per_liter == Decimal('6.4')
    edit = TransactionForm(fuel.user, instance=entry.transaction)
    assert edit['fuel_price_per_liter'].value() == Decimal('6.4')
    assert edit['fuel_calculation_basis'].value() == 'price'


def test_price_basis_recalculates_liters_on_total_change(fuel):
    form = TransactionForm(fuel.user, data_for(
        fuel.transaction, value='128', fuel_liters='40', fuel_price_per_liter='6.4', fuel_calculation_basis='price',
    ), instance=fuel.transaction)
    assert form.is_valid(), form.errors
    assert form.cleaned_data['fuel_liters'] == Decimal('20')


def test_measured_liters_override_previous_price_basis(fuel):
    FuelEntry.objects.create(transaction=fuel.transaction, liters=40, amount_paid=240, informed_price_per_liter='6')
    form = TransactionForm(fuel.user, data_for(
        fuel.transaction, value='220', fuel_price_per_liter='6', fuel_calculation_basis='liters',
    ), instance=fuel.transaction)
    assert form.is_valid(), form.errors
    TransactionService.update(form, fuel.transaction)
    entry = FuelEntry.objects.get(transaction=fuel.transaction)
    assert entry.informed_price_per_liter is None
    assert entry.price_per_liter == Decimal('5.5')


@pytest.mark.parametrize('price', ['0', '-1', '0.00001'])
def test_invalid_informed_price_is_rejected(fuel, price):
    form = TransactionForm(fuel.user, data_for(
        fuel.transaction, fuel_liters='', fuel_price_per_liter=price,
    ), instance=fuel.transaction)
    assert not form.is_valid()
    assert 'fuel_price_per_liter' in form.errors


def test_expense_form_works_without_type_field(fuel):
    posted = data_for(fuel.transaction)
    posted.pop('id')
    posted.pop('type')
    form = TransactionExpenseForm(fuel.user, posted)
    assert form.is_valid(), form.errors
    transaction = TransactionService.create(form, fuel.user)
    assert FuelEntry.objects.filter(transaction=transaction).exists()


@pytest.mark.parametrize('changes,field', [
    ({'fuel_liters': ''}, 'fuel_liters'),
    ({'fuel_liters': '0'}, 'fuel_liters'),
    ({'fuel_distance_km': '0'}, 'fuel_distance_km'),
    ({'fuel_odometer_km': '-1'}, 'fuel_odometer_km'),
    ({'value': '0'}, 'value'),
    ({'type': 'entrada'}, 'category'),
])
def test_invalid_fuel_data_is_rejected(fuel, changes, field):
    form = TransactionForm(fuel.user, data_for(fuel.transaction, **changes), instance=fuel.transaction)
    assert not form.is_valid()
    assert field in form.errors


def test_unrelated_edit_without_marker_preserves_fuel(fuel):
    entry = FuelEntry.objects.create(transaction=fuel.transaction, liters=40, amount_paid=240)
    form = TransactionForm(fuel.user, model_to_dict(fuel.transaction), instance=fuel.transaction)
    assert form.is_valid(), form.errors
    TransactionService.update(form, fuel.transaction)
    entry.refresh_from_db()
    assert entry.liters == 40


def test_remove_and_transaction_delete_are_supported(fuel):
    FuelEntry.objects.create(transaction=fuel.transaction, liters=40, amount_paid=240)
    form = TransactionForm(fuel.user, data_for(fuel.transaction, fuel_remove='on'), instance=fuel.transaction)
    assert form.is_valid(), form.errors
    TransactionService.update(form, fuel.transaction)
    assert not FuelEntry.objects.exists()
    FuelEntry.objects.create(transaction=fuel.transaction, liters=40, amount_paid=240)
    TransactionService.delete(fuel.transaction)
    assert not FuelEntry.objects.exists()


def test_deleting_refueling_marks_next_interval_as_incomplete(fuel):
    FuelEntry.objects.create(transaction=fuel.transaction, liters=40, amount_paid=240)
    next_transaction = Transaction.objects.create(
        user=fuel.user, category=fuel.category, subcategory=fuel.subcategory, currency=fuel.currency,
        posted_date=date(2026, 1, 2), payment_date=date(2026, 1, 2), value=240,
    )
    following = FuelEntry.objects.create(transaction=next_transaction, liters=40, amount_paid=240)
    TransactionService.delete(fuel.transaction)
    following.refresh_from_db()
    assert following.break_before is True


def test_break_allows_odometer_restart_without_bridging_periods(fuel):
    FuelEntry.objects.create(transaction=fuel.transaction, liters=40, amount_paid=240, odometer_km=1000)
    form = TransactionExpenseForm(fuel.user, data_for(
        fuel.transaction, posted_date='2026-01-02', fuel_odometer_km='100', fuel_break_before='on',
    ))
    assert form.is_valid(), form.errors


def test_clearing_existing_fields_requires_explicit_removal(fuel):
    FuelEntry.objects.create(transaction=fuel.transaction, liters=40, amount_paid=240)
    form = TransactionForm(fuel.user, data_for(
        fuel.transaction, fuel_liters='', fuel_odometer_km='', fuel_distance_km='',
    ), instance=fuel.transaction)
    assert not form.is_valid()
    assert 'fuel_liters' in form.errors


def test_fuel_write_rolls_back_transaction_on_error(fuel, mocker):
    form = TransactionForm(fuel.user, data_for(fuel.transaction))
    assert form.is_valid(), form.errors
    count = Transaction.objects.count()
    mocker.patch.object(form, 'save_fuel_entry', side_effect=ValueError('failed'))
    with pytest.raises(ValueError):
        TransactionService.create(form, fuel.user)
    assert Transaction.objects.count() == count


def test_retroactive_edit_is_checked_against_next_reading(fuel):
    FuelEntry.objects.create(transaction=fuel.transaction, liters=40, amount_paid=240, odometer_km=1000, full_tank=True)
    form = TransactionExpenseForm(fuel.user, data_for(fuel.transaction, fuel_odometer_km='1200', posted_date='2025-12-31'))
    assert not form.is_valid()
    assert 'fuel_odometer_km' in form.errors


def test_history_is_scoped_to_owner_and_uses_purchase_date(fuel):
    FuelEntry.objects.create(transaction=fuel.transaction, liters=40, amount_paid=240)
    other = User.objects.create(username='other', email='other@test.invalid')
    assert fuel_history(other) == []
    assert fuel_history(fuel.user)[0]['date'] == '2026-01-01'


def test_installments_do_not_duplicate_refueling_or_divide_total_paid(fuel):
    posted = data_for(fuel.transaction, installments_number=3, paid=0)
    form = TransactionForm(fuel.user, posted)
    assert form.is_valid(), form.errors
    transaction = TransactionService.create(form, fuel.user)
    InstallmentService.create(form, user=fuel.user, transaction=transaction)
    assert transaction.value == 80
    assert FuelEntry.objects.count() == 1
    entry = FuelEntry.objects.get(transaction=transaction)
    assert entry.amount_paid == 240
    edit = TransactionForm(fuel.user, data_for(transaction, fuel_amount_paid='240'), instance=transaction)
    assert edit.is_valid(), edit.errors
    TransactionService.update(edit, transaction)
    entry.refresh_from_db()
    assert entry.price_per_liter == 6


def test_legacy_import_is_idempotent_preserves_text_and_does_not_infer_tank(fuel):
    migration = import_module('statement.migrations.0021_import_legacy_fuel_entries')
    original = '''Meu comentário
########## CÁLCULOS DE COMBUSTÍVEL ##########
CUSTO: R$ — por km.
CONSUMO: 0.0 km/l.
PREÇO: R$ 6.4.
LITROS: 36.9 l.
DISTÂNCIA: 0 km.
QUILOMETRAGEM: 82802 km
#########################################'''
    fuel.transaction.observation = original
    fuel.transaction.save()
    editor = SimpleNamespace(connection=connection)
    migration.import_entries(apps, editor)
    migration.import_entries(apps, editor)
    entry = FuelEntry.objects.get(transaction=fuel.transaction)
    assert entry.liters == Decimal('36.9')
    assert entry.distance_km is None
    assert entry.odometer_km == 82802
    assert entry.full_tank is None
    assert entry.transaction.observation == original


def test_legacy_configuration_enables_existing_workflow_without_magic_ids(fuel):
    migration = import_module('statement.migrations.0022_configure_legacy_fuel_tracking')
    profile = Profile.objects.get(user=fuel.user)
    profile.fuel_subcategory = None
    profile.enable_fuel_tracking = False
    profile.save()
    FuelEntry.objects.create(transaction=fuel.transaction, liters=40, amount_paid=240)
    migration.configure_tracking(apps, SimpleNamespace(connection=connection))
    profile.refresh_from_db()
    assert profile.enable_fuel_tracking
    assert profile.fuel_subcategory == fuel.subcategory


def test_legacy_configuration_preserves_explicit_disabled_preference(fuel):
    migration = import_module('statement.migrations.0022_configure_legacy_fuel_tracking')
    Profile.objects.filter(user=fuel.user).update(enable_fuel_tracking=False)
    FuelEntry.objects.create(transaction=fuel.transaction, liters=40, amount_paid=240)
    migration.configure_tracking(apps, SimpleNamespace(connection=connection))
    assert Profile.objects.get(user=fuel.user).enable_fuel_tracking is False
