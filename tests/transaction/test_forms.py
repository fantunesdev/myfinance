from datetime import date
from types import SimpleNamespace

import pytest
from django.forms import model_to_dict

from login.models import User
from statement.forms.core.transaction import TransactionExpenseForm, TransactionForm, TransactionRevenueForm
from statement.models import Category, Currency, Subcategory, Transaction
from statement.services.core.category import CategoryService
from statement.services.core.subcategory import SubcategoryService
from statement.views.core.transaction import TransactionView


@pytest.fixture
def classification(db):
    user = User.objects.create(username='transaction-form', email='transaction-form@test.invalid')
    expense = Category.objects.create(description='Alimentação', type='saida')
    other_expense = Category.objects.create(description='Transporte', type='saida')
    revenue = Category.objects.create(description='Receitas', type='entrada')
    groceries = Subcategory.objects.create(description='Mercado', category=expense)
    restaurants = Subcategory.objects.create(description='Restaurantes', category=expense)
    transport = Subcategory.objects.create(description='Ônibus', category=other_expense)
    salary = Subcategory.objects.create(description='Salário', category=revenue)
    currency, _ = Currency.objects.get_or_create(id='BRL', defaults={'description': 'Real', 'symbol': 'R$'})
    transaction = Transaction.objects.create(
        user=user,
        category=expense,
        subcategory=groceries,
        currency=currency,
        posted_date=date(2026, 11, 1),
        payment_date=date(2026, 11, 1),
        description='Compras',
        value=100,
        type='saida',
    )
    return SimpleNamespace(**locals())


@pytest.mark.parametrize('transaction_type', ['entrada', 'saida'])
def test_edit_form_filters_options_and_preserves_selection(classification, transaction_type):
    data = classification
    transaction = data.transaction
    transaction.type = transaction_type
    transaction.category = data.revenue if transaction_type == 'entrada' else data.expense
    transaction.subcategory = data.salary if transaction_type == 'entrada' else data.groceries
    view = TransactionView()
    view._context = 'update'

    form = view._set_form(SimpleNamespace(user=data.user, method='GET'), transaction)

    assert set(form.fields['category'].queryset) == (
        {data.revenue} if transaction_type == 'entrada' else {data.expense, data.other_expense}
    )
    assert set(form.fields['subcategory'].queryset) == (
        {data.salary} if transaction_type == 'entrada' else {data.groceries, data.restaurants}
    )
    assert form['category'].value() == transaction.category_id
    assert form['subcategory'].value() == transaction.subcategory_id


@pytest.mark.parametrize('change_type', [False, True])
def test_edit_form_accepts_new_category_and_subcategory(classification, change_type):
    data = classification
    category = data.revenue if change_type else data.other_expense
    subcategory = data.salary if change_type else data.transport
    posted = {
        **model_to_dict(data.transaction),
        'type': category.type,
        'category': str(category.pk),
        'subcategory': str(subcategory.pk),
    }
    form = TransactionForm(data.user, posted, instance=data.transaction)

    assert set(form.fields['subcategory'].queryset) == {subcategory}
    assert form.is_valid(), form.errors
    form.save()
    data.transaction.refresh_from_db()
    assert data.transaction.type == category.type
    assert data.transaction.category == category
    assert data.transaction.subcategory == subcategory


def test_edit_form_rejects_category_from_another_type(classification):
    data = classification
    posted = {
        **model_to_dict(data.transaction),
        'category': str(data.revenue.pk),
        'subcategory': str(data.salary.pk),
    }
    form = TransactionForm(data.user, posted, instance=data.transaction)

    assert not form.is_valid()
    assert 'category' in form.errors
    assert not form.fields['subcategory'].queryset.exists()


def test_edit_form_rejects_subcategory_from_another_category(classification):
    data = classification
    posted = {**model_to_dict(data.transaction), 'subcategory': str(data.transport.pk)}
    form = TransactionForm(data.user, posted, instance=data.transaction)

    assert not form.is_valid()
    assert 'subcategory' in form.errors


@pytest.mark.parametrize('category', ['', '0', 'invalid', '999999'])
def test_edit_form_does_not_fall_back_to_existing_category_on_invalid_post(classification, category):
    data = classification
    posted = {**model_to_dict(data.transaction), 'category': category}
    form = TransactionForm(data.user, posted, instance=data.transaction)

    assert not form.fields['subcategory'].queryset.exists()
    assert not form.is_valid()
    assert 'category' in form.errors


@pytest.mark.parametrize('form_class', [TransactionExpenseForm, TransactionRevenueForm])
def test_create_form_filters_categories_and_waits_for_category_to_show_subcategories(classification, form_class):
    data = classification
    form = form_class(data.user)

    assert {category.type for category in form.fields['category'].queryset} == {form_class.transaction_type}
    assert not form.fields['subcategory'].queryset.exists()


def test_category_and_subcategory_lists_are_alphabetical(classification):
    data = classification
    Category.objects.create(description='Zoológico', type='saida')
    accommodation = Category.objects.create(description='Acomodação', type='saida')
    Subcategory.objects.create(description='Zoológico', category=data.expense)
    activities = Subcategory.objects.create(description='Atividades', category=data.expense)

    assert list(CategoryService.get_all().values_list('description', flat=True)) == [
        'Acomodação',
        'Alimentação',
        'Receitas',
        'Transporte',
        'Zoológico',
    ]
    assert list(CategoryService.get_by_type('saida')) == [
        accommodation,
        data.expense,
        data.other_expense,
        Category.objects.get(description='Zoológico'),
    ]
    assert SubcategoryService.get_all().first() == activities
    assert list(SubcategoryService.get_by_category(data.expense.pk).values_list('description', flat=True)) == [
        'Atividades',
        'Mercado',
        'Restaurantes',
        'Zoológico',
    ]
    form = TransactionForm(data.user, instance=data.transaction)
    assert list(form.fields['category'].queryset) == list(CategoryService.get_by_type('saida'))
    assert list(form.fields['subcategory'].queryset) == list(SubcategoryService.get_by_category(data.expense.pk))


def test_edit_without_source_category_preserves_bank_metadata(classification):
    from statement.services.core.transaction import TransactionService

    transaction = classification.transaction
    transaction.source_category = 'SUPERMERCADO'
    transaction.save()
    posted = model_to_dict(transaction)
    posted.pop('source_category')
    form = TransactionForm(classification.user, posted, instance=transaction)
    assert form.is_valid(), form.errors
    TransactionService.update(form, transaction)
    transaction.refresh_from_db()
    assert transaction.source_category == 'SUPERMERCADO'
