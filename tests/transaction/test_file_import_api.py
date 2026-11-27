import csv
import io
import json

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIRequestFactory, force_authenticate

from api.views.transaction import TransactionView
from statement.models import (
    AppConfig,
    CSVImportConfig,
    Notification,
    NotificationTitle,
    NotificationTitlePreference,
    Transaction,
)
from statement.services.core.file_handler import FileHandlerService


def csv_content(rows=None, headers=None, delimiter=';'):
    output = io.StringIO()
    writer = csv.writer(output, delimiter=delimiter)
    writer.writerow(headers or ['Data', 'Descrição', 'Valor', 'Parcela'])
    writer.writerows(rows if rows is not None else [['05/11/2026', 'Mercado', '25,00', '']])
    return output.getvalue()


def preview(ledger, content, **overrides):
    payload = {
        'file': SimpleUploadedFile('import.csv', content.encode('utf-8')),
        'account': ledger.account.pk,
        'card': '',
        'csv_mode': 'configurable',
        'date_column': 'Data',
        'description_column': 'Descrição',
        'value_column': 'Valor',
        'installment_column': 'Parcela',
        **overrides,
    }
    request = APIRequestFactory().post('/api/transactions/import/', payload, format='multipart')
    force_authenticate(request, user=ledger.user)
    return TransactionView.as_view({'post': 'import_transactions'})(request)


@pytest.mark.parametrize('delimiter', [',', ';'])
def test_csv_preview_handles_bom_accents_and_delimiters_without_saving(ledger, delimiter):
    response = preview(ledger, '\ufeff' + csv_content(delimiter=delimiter))
    assert response.status_code == 200
    assert len(response.data) == 1
    row = response.data[0]
    assert row['date'] == '05/11/2026'
    assert row['description'] == row['original_description'] == 'Mercado'
    assert row['value'] == '25.00'
    assert row['account'] == ledger.account.pk
    assert row['source_app'] == 'bank.app'
    assert not row['is_duplicate']
    assert not Transaction.objects.exists()


@pytest.mark.parametrize(
    'amount, expected',
    [
        ('R$ 1.234,56', '1234.56'),
        ('25.5', '25.50'),
        ('-9,90', '-9.90'),
        ('0', '0.00'),
    ],
)
def test_csv_normalizes_brazilian_amounts(ledger, amount, expected):
    response = preview(ledger, csv_content([['05/11/2026', 'Mercado', amount, '']]))
    assert response.status_code == 200
    assert response.data[0]['value'] == expected


@pytest.mark.parametrize(
    'raw, mode, paid, total',
    [
        ('01/03', 'slash', 1, 3),
        ('2 - 12', 'dash', 2, 12),
        ('Parcela 03/10', 'auto', 3, 10),
        ('à vista', 'auto', 0, 0),
    ],
)
def test_csv_parses_configured_installment_column(ledger, raw, mode, paid, total):
    response = preview(ledger, csv_content([['05/11/2026', 'Mercado', '25,00', raw]]), installment_format=mode)
    assert response.status_code == 200
    row = response.data[0]
    assert (row['paid'], row['installments_number']) == (paid, total)
    assert row['installment_text'] == (f'{paid}/{total}' if total else '')


@pytest.mark.parametrize(
    'content, error',
    [
        (csv_content([]), 'vazio'),
        (csv_content([['05/11/2026', 'Mercado']], ['Data', 'Descrição']), 'Valor'),
        (csv_content([['05/11/2026', 'Mercado', '25,00']], ['Data', 'Descrição', 'Valor']), 'Parcela'),
    ],
)
def test_bad_csv_returns_actionable_errors(ledger, content, error):
    response = preview(ledger, content)
    assert response.status_code == 400
    assert error in response.data['errors']
    assert not Transaction.objects.exists()


def test_missing_upload_returns_bad_request(ledger):
    request = APIRequestFactory().post('/api/transactions/import/', {}, format='multipart')
    force_authenticate(request, user=ledger.user)
    response = TransactionView.as_view({'post': 'import_transactions'})(request)
    assert response.status_code == 400
    assert 'Arquivo' in response.data['detail']


@pytest.mark.parametrize('field, relation', [('account', 'other_account'), ('card', 'other_card')])
def test_csv_rejects_another_users_source(ledger, field, relation):
    response = preview(ledger, csv_content(), **{field: getattr(ledger, relation).pk})
    assert response.status_code == 400


def test_saved_config_overrides_request_columns_and_source(ledger):
    config = CSVImportConfig.objects.create(
        user=ledger.user,
        name='Minha importação',
        account=ledger.account,
        date_column='Data',
        description_column='Descrição',
        value_column='Valor',
        installment_column='Parcela',
        matching_fields=['description', 'value'],
    )
    response = preview(ledger, csv_content(), csv_import_config=config.pk, account='', date_column='Wrong')
    assert response.status_code == 200
    assert response.data[0]['account'] == ledger.account.pk
    assert response.data[0]['matching_fields'] == ['description', 'value']


def test_csv_rejects_another_users_saved_configuration(ledger):
    config = CSVImportConfig.objects.create(user=ledger.other, name='Private', account=ledger.other_account)
    response = preview(ledger, csv_content(), csv_import_config_id=config.pk)
    assert response.status_code == 400


@pytest.mark.parametrize('target', ['investment_transaction', 'investments_investmenttransaction'])
def test_investment_csv_keeps_its_target_and_installments(ledger, target, mocker):
    classifier = mocker.patch('statement.services.core.file_handler.TransactionClassifierClient')
    response = preview(ledger, csv_content([['05/11/2026', 'CDB', '100,00', '1/2']]), target_model=target)
    assert response.status_code == 200
    row = response.data[0]
    assert row['target_model'] == target
    assert row['value'] == '100.00'
    assert (row['paid'], row['installments_number']) == (1, 2)
    classifier.assert_not_called()


@pytest.mark.parametrize(
    'fields',
    [
        'posted_date,description,value,account,type',
        'original_description,value',
    ],
)
def test_csv_preview_marks_duplicates_without_creating_records(ledger, entry, fields):
    existing = entry(original_description='Mercado')
    response = preview(ledger, csv_content(), matching_fields=fields)
    assert response.status_code == 200
    assert response.data[0]['is_duplicate']
    assert response.data[0]['duplicate_id'] == existing.pk
    assert Transaction.objects.count() == 1


def test_csv_duplicate_check_does_not_use_another_users_records(ledger, entry):
    entry(user=ledger.other, account=ledger.other_account)
    response = preview(ledger, csv_content(), matching_fields='posted_date,description,value')
    assert response.status_code == 200
    assert not response.data[0]['is_duplicate']
    assert response.data[0]['duplicate_id'] is None


def test_csv_ambiguous_installments_remain_available_for_review(ledger, entry):
    entry(paid=1, installments_number=3)
    entry(paid=1, installments_number=3)
    response = preview(ledger, csv_content([['05/11/2026', 'Mercado', '25,00', '1/3']]))
    assert response.status_code == 200
    assert not response.data[0]['is_duplicate']


def test_csv_installments_can_be_disambiguated_by_original_description(ledger, entry):
    existing = entry(paid=1, installments_number=3, original_description='Mercado')
    entry(paid=1, installments_number=3, original_description='Outra loja')
    response = preview(
        ledger,
        csv_content([['05/11/2026', 'Mercado', '25,00', '1/3']]),
        matching_fields='original_description',
    )
    assert response.status_code == 200
    assert response.data[0]['duplicate_id'] == existing.pk


def test_csv_classifier_failure_keeps_original_values_for_review(ledger, mocker):
    AppConfig.objects.create(enable_transaction_classifier=True)
    client = mocker.patch('statement.services.core.file_handler.TransactionClassifierClient')
    client.return_value.predict.side_effect = RuntimeError('offline')
    response = preview(ledger, csv_content())
    assert response.status_code == 200
    assert response.data[0]['description'] == 'Mercado'
    assert response.data[0]['category'] is None
    client.return_value.predict.assert_called_once()


@pytest.mark.parametrize(
    'description, amount, event',
    [
        ('Pagamento de fatura', '100', 'card_payment'),
        ('Estorno Mercado', '-25', 'refund'),
    ],
)
def test_nonpurchase_csv_events_require_review(ledger, description, amount, event):
    response = preview(ledger, csv_content([['05/11/2026', description, amount, '']]))
    assert response.status_code == 200
    assert response.data[0]['event_type'] == event
    assert response.data[0]['needs_review']
    assert response.data[0]['review_reason']


def test_csv_fixed_expense_is_annotated_instead_of_classified_again(ledger, entry, mocker):
    existing = entry(fixed=True, event_type='fixed_expense', source_type='csv', original_description='Mercado')
    client = mocker.patch('statement.services.core.file_handler.TransactionClassifierClient')
    response = preview(ledger, csv_content())
    assert response.status_code == 200
    assert response.data[0]['ignored_fixed_expense']
    assert response.data[0]['fixed_transaction_id'] == existing.pk
    client.assert_not_called()


@pytest.fixture
def tasker(ledger):
    title = NotificationTitle.objects.create(title='Compra')
    NotificationTitlePreference.objects.create(user=ledger.user, title=title, enabled=True)

    def upload(rows):
        text = '\n'.join(json.dumps(row, ensure_ascii=False) for row in rows)
        return preview(ledger, text, import_type='tasker_json')

    return upload


def notification(**overrides):
    return {
        'app': 'bank.app',
        'title': 'Compra',
        'message': 'Compra de R$ 25,90 em Loja.',
        'date': '2026-11-05 12:30:00',
        **overrides,
    }


def test_tasker_preview_filters_disabled_titles_and_extracts_amount(ledger, tasker):
    response = tasker([notification(), notification(title='Propaganda')])
    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]['value'] == 25.9
    assert response.data[0]['date'] == '2026-11-05 12:30:00'
    assert not Notification.objects.exists()


@pytest.mark.parametrize('missing', ['app', 'title', 'message', 'date'])
def test_tasker_reports_missing_required_fields(ledger, tasker, missing):
    row = notification()
    row.pop(missing)
    response = tasker([row])
    assert response.status_code == 400
    assert missing in response.data['errors']
    assert 'linha 1' in response.data['errors']


def test_tasker_reports_malformed_json_line(ledger, tasker):
    response = preview(ledger, '\n{invalid}', import_type='tasker_json')
    assert response.status_code == 400
    assert 'linha 2' in response.data['errors']


def test_tasker_skips_existing_notifications_for_the_same_user(ledger, tasker):
    data = notification()
    Notification.objects.create(user=ledger.user, **{key: value for key, value in data.items() if key != 'date'})
    response = tasker([data, notification(message='Compra de R$ 50,00 em Outra loja.')])
    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]['value'] == 50


def test_tasker_duplicate_check_does_not_use_another_users_notifications(ledger, tasker):
    data = notification()
    Notification.objects.create(user=ledger.other, **{key: value for key, value in data.items() if key != 'date'})
    response = tasker([data])
    assert response.status_code == 200
    assert len(response.data) == 1


def test_tasker_no_enabled_notifications_returns_bad_request(ledger, tasker):
    response = tasker([notification(title='Disabled')])
    assert response.status_code == 400
    assert 'Nenhuma notificação' in response.data['errors']


def test_unsupported_file_reader_format_is_rejected():
    with pytest.raises(ValueError, match='Unsupported file format'):
        FileHandlerService.read_file(None, file_type='xml')


@pytest.mark.parametrize('valid_category', [True, False])
def test_csv_prediction_uses_category_type_and_tolerates_stale_category_ids(ledger, mocker, valid_category):
    AppConfig.objects.create(enable_transaction_classifier=True)
    client = mocker.patch('statement.services.core.file_handler.TransactionClassifierClient')
    client.return_value.predict.return_value = {
        'category_id': ledger.category.pk if valid_category else 999999,
        'subcategory_id': ledger.subcategory.pk if valid_category else None,
        'description': 'Mercado classificado',
    }
    response = preview(ledger, csv_content())
    assert response.status_code == 200
    assert response.data[0]['description'] == 'Mercado classificado'
    assert response.data[0]['type'] == 'saida'


def test_card_csv_installment_duplicate_uses_the_owned_card_without_an_account(ledger, entry):
    existing = entry(account=None, card=ledger.card, paid=1, installments_number=3)
    response = preview(
        ledger, csv_content([['05/11/2026', 'Mercado', '25,00', '1/3']]), account='', card=ledger.card.pk
    )
    assert response.status_code == 200
    assert response.data[0]['duplicate_id'] == existing.pk


def test_csv_unknown_installment_disambiguator_keeps_rows_for_manual_review(ledger, entry):
    entry(paid=1, installments_number=3)
    response = preview(ledger, csv_content([['05/11/2026', 'Mercado', '25,00', '1/3']]), matching_fields='unknown')
    assert response.status_code == 200
    assert not response.data[0]['is_duplicate']


def test_csv_duplicate_filters_use_the_selected_card_and_predicted_categories(ledger, entry, mocker):
    existing = entry(account=None, card=ledger.card)
    AppConfig.objects.create(enable_transaction_classifier=True)
    mocker.patch(
        'statement.services.core.file_handler.TransactionClassifierClient'
    ).return_value.predict.return_value = {
        'description': 'Mercado',
        'category_id': ledger.category.pk,
        'subcategory_id': ledger.subcategory.pk,
    }
    response = preview(
        ledger, csv_content(), account='', card=ledger.card.pk, matching_fields='card,category,subcategory,type'
    )
    assert response.status_code == 200
    assert response.data[0]['duplicate_id'] == existing.pk


def test_tasker_preview_remains_available_when_optional_title_preferences_fail(ledger, mocker):
    mocker.patch(
        'statement.services.core.notification_title.NotificationTitleService.get_enabled_titles_for_user',
        side_effect=RuntimeError('unavailable'),
    )
    response = preview(ledger, json.dumps(notification()), import_type='tasker_json')
    assert response.status_code == 200
    assert response.data[0]['value'] == 25.9
