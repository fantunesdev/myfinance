from io import BytesIO
from pathlib import Path

import pytest
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import Http404
from django.template.loader import render_to_string
from django.test import RequestFactory, override_settings
from django.utils.datastructures import MultiValueDict
from reportlab.pdfgen.canvas import Canvas

from login.models import User
from statement.forms.dream.document import DreamDocumentForm
from statement.models import Dream, DreamDocument
from statement.views.dream.dream import DreamView


def pdf_file(name='Nota fiscal.pdf'):
    buffer = BytesIO()
    canvas = Canvas(buffer)
    canvas.drawString(40, 800, 'Nota fiscal de teste')
    canvas.save()
    return SimpleUploadedFile(name, buffer.getvalue(), content_type='application/pdf')


@pytest.fixture
def records(db, tmp_path):
    with override_settings(MEDIA_ROOT=tmp_path, ROOT_URLCONF='statement.urls.dream.dream', LOGIN_URL='/login/'):
        owner = User.objects.create(username='document-owner', email='document-owner@example.com')
        other = User.objects.create(username='document-other', email='document-other@example.com')
        dream = Dream.objects.create(user=owner, description='Viagem')
        yield owner, other, dream


def request_for(user, method='post', data=None):
    request = getattr(RequestFactory(), method)('/documentos/', data=data or {})
    request.user = user
    request.session = {}
    request._messages = FallbackStorage(request)
    return request


def document_for(dream):
    file = pdf_file()
    return DreamDocument.objects.create(dream=dream, file=file, name=file.name, size=file.size)


def test_upload_multiple_pdfs_preserves_names_and_contents(records):
    owner, _, dream = records
    files = [pdf_file(), pdf_file()]
    contents = [file.read() for file in files]
    for file in files:
        file.seek(0)
    response = DreamView().upload_documents(request_for(owner, data={'documents': files}), dream.pk)
    assert response.status_code == 302
    documents = list(dream.documents.all())
    assert len(documents) == 2
    assert documents[0].file.name != documents[1].file.name
    assert [document.name for document in documents] == ['Nota fiscal.pdf', 'Nota fiscal.pdf']
    for document, expected in zip(documents, contents):
        with document.file.open('rb') as stored:
            assert stored.read() == expected
        assert document.size == len(expected)
    html = render_to_string(
        'dream/documents.html',
        {
            'instance': dream,
            'documents': documents,
            'document_form': DreamDocumentForm(),
        },
    )
    assert 'Nota fiscal.pdf' in html
    assert 'Nenhum documento ainda.' not in html


@pytest.mark.parametrize('invalid', ['text', 'image', 'extension', 'oversized'])
def test_invalid_batch_saves_nothing_and_keeps_existing_documents(records, monkeypatch, invalid):
    owner, _, dream = records
    existing = document_for(dream)
    bad = {
        'text': lambda: SimpleUploadedFile('fake.pdf', b'not a pdf', content_type='application/pdf'),
        'image': lambda: SimpleUploadedFile('fake.pdf', b'GIF89a' + b'0' * 100, content_type='application/pdf'),
        'extension': lambda: pdf_file('invoice.html'),
        'oversized': lambda: SimpleUploadedFile('large.pdf', b'x' * (10 * 1024 * 1024 + 1)),
    }[invalid]()
    view = DreamView()
    monkeypatch.setattr(view, '_render', lambda request, form, template, context: context)
    context = view.upload_documents(request_for(owner, data={'documents': [pdf_file(), bad]}), dream.pk)
    assert context['document_form'].errors
    assert list(context['documents']) == [existing]
    assert 'photo_form' in context


def test_empty_and_too_many_documents_are_rejected(records):
    assert not DreamDocumentForm({}, MultiValueDict()).is_valid()
    assert not DreamDocumentForm({}, {'documents': [pdf_file() for _ in range(11)]}).is_valid()


@pytest.mark.parametrize('action', ['upload_documents', 'document', 'delete_document'])
def test_document_actions_require_ownership(records, action):
    _, other, dream = records
    document = document_for(dream)
    kwargs = {'id': dream.pk}
    if action != 'upload_documents':
        kwargs['document_id'] = document.pk
    with pytest.raises(Http404):
        getattr(DreamView(), action)(request_for(other, 'get' if action == 'document' else 'post'), **kwargs)
    assert dream.documents.count() == 1


def test_document_cannot_be_accessed_under_another_dream(records):
    owner, _, dream = records
    document = document_for(dream)
    other_dream = Dream.objects.create(user=owner, description='Outro sonho')
    with pytest.raises(Http404):
        DreamView().document(request_for(owner, 'get'), other_dream.pk, document.pk)


@pytest.mark.parametrize('download', [False, True])
def test_owner_can_open_and_download_pdf(records, download):
    owner, _, dream = records
    document = document_for(dream)
    request = request_for(owner, 'get', {'download': '1'} if download else {})
    response = DreamView().document(request, dream.pk, document.pk)
    assert response.status_code == 200
    assert response['Content-Type'] == 'application/pdf'
    assert response['Content-Disposition'].startswith('attachment;' if download else 'inline;')
    assert response['Cache-Control'] == 'private, no-store'
    assert b''.join(response.streaming_content).startswith(b'%PDF-')
    response.close()


@pytest.mark.parametrize('delete_dream', [False, True])
def test_deleting_document_or_dream_removes_file_after_commit(
    records, django_capture_on_commit_callbacks, delete_dream
):
    owner, _, dream = records
    document = document_for(dream)
    storage, name = document.file.storage, document.file.name
    with django_capture_on_commit_callbacks(execute=True):
        if delete_dream:
            dream.delete()
        else:
            response = DreamView().delete_document(request_for(owner), dream.pk, document.pk)
            assert response.status_code == 302
        assert storage.exists(name)
    assert not storage.exists(name)


@pytest.mark.parametrize('action', ['upload_documents', 'delete_document'])
def test_document_mutations_reject_get(records, action):
    owner, _, dream = records
    kwargs = {'id': dream.pk}
    if action == 'delete_document':
        kwargs['document_id'] = 1
    assert getattr(DreamView(), action)(request_for(owner, 'get'), **kwargs).status_code == 405


def test_anonymous_cannot_read_document(records):
    response = DreamView().document(request_for(AnonymousUser(), 'get'), records[2].pk, 1)
    assert response.status_code == 302
    assert '/login/' in response.url


def test_database_failure_rolls_back_batch_and_removes_files(records, monkeypatch):
    owner, _, dream = records
    original_save = DreamDocument.save

    def fail_second_save(instance, *args, **kwargs):
        original_save(instance, *args, **kwargs)
        if dream.documents.count() == 2:
            raise RuntimeError('Failed batch')

    monkeypatch.setattr(DreamDocument, 'save', fail_second_save)
    with pytest.raises(RuntimeError, match='Failed batch'):
        DreamView().upload_documents(request_for(owner, data={'documents': [pdf_file(), pdf_file()]}), dream.pk)
    assert not dream.documents.exists()
    storage = DreamDocument._meta.get_field('file').storage
    assert not list(Path(storage.location).rglob('*.pdf'))
