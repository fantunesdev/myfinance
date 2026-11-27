from datetime import date
from types import SimpleNamespace

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from api.views.transaction import TransactionView
from statement.services.core.file_handler import FileHandlerService


@pytest.fixture
def handler(ledger):
    return FileHandlerService(
        SimpleNamespace(
            user=ledger.user,
            FILES={'file': SimpleUploadedFile('test.csv', b'date,title,amount\n')},
            data={'account': '', 'card': '', 'matching_fields': ['description', 'value']},
        )
    )


@pytest.mark.parametrize(
    'raw, expected',
    [
        (None, None),
        ('', None),
        ('invalid', None),
        ('05/11/2026', date(2026, 11, 5)),
        ('2026-11-05', date(2026, 11, 5)),
        ('November 5, 2026', date(2026, 11, 5)),
    ],
)
def test_duplicate_detection_normalizes_supported_dates_without_guessing_invalid_dates(handler, raw, expected):
    assert handler._normalize_date(raw) == expected
    assert TransactionView()._normalize_date(raw) == expected


@pytest.mark.parametrize(
    'raw, expected', [(None, ''), ('invalid', 'invalid'), ('R$ 1.000,30', '1000.30'), ('10,5', '10.50')]
)
def test_csv_amount_normalization_preserves_invalid_values_for_review(handler, raw, expected):
    assert handler._normalize_value(raw) == expected


def test_extra_csv_columns_without_headers_are_ignored(handler):
    assert handler._normalize_csv_row({None: ['extra'], ' date ': '2026-11-05'}) == {'date': '2026-11-05'}
    assert handler._normalize_csv_header(None) == ''
    handler._installment_column = 'Parcela'
    assert handler._extract_installment_text({}) == ''
    assert handler._parse_installment_numbers('invalid') == (0, 0)


@pytest.mark.parametrize(
    'fields, data, expected',
    [
        ('card', {'card': 1}, {'card_id': 1}),
        ('card', {}, {'card__isnull': True}),
        ('card_number', {'card_number': 2}, {'card_number_id': 2}),
        ('card_number', {}, {'card_number__isnull': True}),
        ('category', {}, None),
        ('subcategory', {}, None),
        ('unsupported', {}, None),
        ('value', {'value': 'invalid'}, None),
    ],
)
def test_api_duplicate_filter_refuses_incomplete_or_invalid_keys(fields, data, expected):
    assert TransactionView()._build_duplicate_filter(fields, data) == expected


@pytest.mark.parametrize(
    'field, data',
    [
        ('card_number', {}),
        ('category', {}),
        ('subcategory', {}),
        ('unsupported', {}),
        ('value', {'value': 'invalid'}),
    ],
)
def test_csv_duplicate_filter_does_not_claim_a_match_for_unknown_data(handler, field, data):
    assert handler._build_duplicate_filter(field, data) is None


@pytest.mark.parametrize('field, expected', [('account', {'account__isnull': True}), ('card', {'card__isnull': True})])
def test_duplicate_detection_distinguishes_missing_payment_sources(handler, field, expected):
    assert handler._build_duplicate_filter(field, {}) == expected


def test_legacy_csv_uses_default_columns_and_unmodified_values(ledger):
    request = SimpleNamespace(
        user=ledger.user,
        data={'account': '', 'card': ''},
        FILES={
            'file': SimpleUploadedFile('test.csv', b'date,title,amount\n2026-11-05,Mercado,25.00\n'),
        },
    )
    rows = FileHandlerService(request).read_file()
    assert rows[0]['date'] == '2026-11-05'
    assert rows[0]['description'] == 'Mercado'
    assert rows[0]['value'] == '25.00'


def test_csv_reader_falls_back_when_dialect_detection_fails(handler):
    reader = handler._get_csv_reader('date,title,amount\n2026-11-05,Only two\n')
    row = next(reader)
    assert row['title'] == 'Only two'
    assert row['amount'] is None


def test_duplicate_matching_without_a_date_does_not_match_installments(handler):
    assert handler._find_installment_duplicate({'installments_number': 3, 'paid': 1}) is None
    request = SimpleNamespace(user=handler._user, data={'installments_number': 3})
    assert TransactionView()._find_installment_duplicate(request) is None


def test_unknown_duplicate_rules_leave_the_row_for_review(handler):
    handler._matching_fields = ['unsupported']
    assert handler._find_duplicate_transaction({'description': 'Mercado'}) is None
    assert handler._narrow_installment_duplicates(None, {}, ['unsupported']) is None


def test_empty_installment_text_resets_previous_parser_state():
    view = TransactionView()
    assert view._get_installments_number('Compra 1/3') == 3
    assert view._get_installments_number(None) == 0
    assert view.installment_info is None
    assert view._get_current_installment_number() == 1
