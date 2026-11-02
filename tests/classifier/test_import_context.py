from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from clients.transaction_classifier.subcategory_predictor import SubcategoryPredictorClient
from login.models import User
from statement.models import CategorizationFeedback
from statement.services.core import classifier_jobs as jobs
from statement.services.core.file_handler import FileHandlerService


@pytest.mark.parametrize('header', ['Categoria', 'category', 'CATEGORIA', 'categória'])
def test_csv_category_header_is_recognized(header):
    assert FileHandlerService._extract_source_category({header: ' SUPERMERCADO '}) == 'SUPERMERCADO'


def test_missing_bank_category_is_optional():
    assert FileHandlerService._extract_source_category({'description': 'Loja'}) == ''


def test_csv_import_preserves_bank_category_and_calls_predictor_with_separate_context():
    content = '"Data","Lançamento","Categoria","Tipo","Valor"\n"27/10/2026","GREBOE CIA LTDA ME","SUPERMERCADO","Compra à vista","R$ 9,60"\n'
    upload = SimpleUploadedFile('exemplo.csv', content.encode('utf-8'))
    user = SimpleNamespace(id=1)
    request = SimpleNamespace(FILES={'file': upload}, user=user, data={
        'csv_mode': 'configurable', 'date_column': 'Data', 'description_column': 'Lançamento',
        'value_column': 'Valor', 'account': '', 'card': '',
    })
    with patch('statement.services.core.file_handler.AppConfig') as config, patch(
        'statement.services.core.file_handler.TransactionClassifierClient'
    ) as factory, patch.object(FileHandlerService, '_find_duplicate_transaction', return_value=None):
        config.get_solo.return_value.enable_transaction_classifier = True
        factory.return_value.predict.return_value = {'category_id': None, 'subcategory_id': None, 'description': 'Mercado'}
        rows = FileHandlerService(request).read_file()
    factory.return_value.predict.assert_called_once_with('GREBOE CIA LTDA ME', source_category='SUPERMERCADO', source_type='csv', source_app='', event_type='purchase', merchant_description='GREBOE CIA LTDA ME')
    assert rows[0]['source_category'] == 'SUPERMERCADO'
    assert rows[0]['original_description'] == 'GREBOE CIA LTDA ME'
    assert rows[0]['description'] == 'Mercado'


def test_client_forwards_source_category_without_treating_it_as_internal_category():
    client = object.__new__(SubcategoryPredictorClient)
    with patch.object(client, '_send_requisition', return_value={}) as send:
        client.predict('GREBOE', source_category='SUPERMERCADO')
    assert send.call_args.args[2] == {'description': 'GREBOE', 'category': '', 'source_category': 'SUPERMERCADO'}


@pytest.mark.django_db
def test_feedback_job_snapshot_preserves_original_bank_category():
    user = User.objects.create(username='bank-context', email='context@test.invalid')
    CategorizationFeedback.objects.create(user=user, description='GREBOE', corrected_description='Mercado', source_category='SUPERMERCADO')
    job = jobs.create_job(user, 'subcategory', 'feedback')
    assert job.feedbacks[0]['source_category'] == 'SUPERMERCADO'
