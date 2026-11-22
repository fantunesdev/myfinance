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
from PIL import Image

from login.models import User
from statement.forms.dream.photo import DreamPhotoForm
from statement.models import Dream, DreamPhoto
from statement.views.dream.dream import DreamView


def image_file(name='photo.png'):
    buffer = BytesIO()
    Image.new('RGB', (20, 15), 'green').save(buffer, format='PNG')
    return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/png')


@pytest.fixture
def records(db, tmp_path):
    with override_settings(
        MEDIA_ROOT=tmp_path,
        ROOT_URLCONF='statement.urls.dream.dream',
        LOGIN_URL='/login/',
    ):
        owner = User.objects.create(username='photo-owner', email='photo-owner@example.com')
        other = User.objects.create(username='photo-other', email='photo-other@example.com')
        dream = Dream.objects.create(user=owner, description='Viagem')
        yield owner, other, dream


def request_for(user, method='post', data=None):
    request = getattr(RequestFactory(), method)('/sonhos/1/fotos/', data=data or {})
    request.user = user
    request.session = {}
    request._messages = FallbackStorage(request)
    return request


def test_upload_multiple_photos_in_order_and_render_gallery(records):
    owner, _, dream = records
    response = DreamView().upload_photos(
        request_for(owner, data={'photos': [image_file(), image_file()]}),
        dream.pk,
    )
    assert response.status_code == 302
    photos = list(dream.photos.all())
    assert len(photos) == 2
    assert photos[0].pk < photos[1].pk
    assert photos[0].image.name != photos[1].image.name
    assert all(photo.image.storage.exists(photo.image.name) for photo in photos)
    html = render_to_string(
        'dream/photos.html',
        {'instance': dream, 'photos': photos, 'photo_form': DreamPhotoForm()},
    )
    assert 'data-photo-index="0"' in html
    assert 'data-photo-index="1"' in html
    assert '<dialog' in html


@pytest.mark.parametrize(
    'bad_file',
    [
        SimpleUploadedFile('not-image.png', b'not an image', content_type='image/png'),
        SimpleUploadedFile(
            'too-big.png',
            b'x' * (10 * 1024 * 1024 + 1),
            content_type='image/png',
        ),
    ],
)
def test_invalid_batch_saves_no_photos_and_preserves_gallery(records, monkeypatch, bad_file):
    owner, _, dream = records
    existing = DreamPhoto.objects.create(dream=dream, image=image_file())
    view = DreamView()
    monkeypatch.setattr(view, '_render', lambda request, form, template, context: context)
    context = view.upload_photos(request_for(owner, data={'photos': [image_file(), bad_file]}), dream.pk)
    assert context['photo_form'].errors
    assert list(context['photos']) == [existing]


def test_upload_limits_and_empty_input(records):
    assert not DreamPhotoForm({}, {}).is_valid()
    assert not DreamPhotoForm({}, MultiValueDict()).is_valid()
    form = DreamPhotoForm({}, {'photos': [image_file() for _ in range(11)]})
    assert not form.is_valid()
    assert '10 fotos' in str(form.errors)


@pytest.mark.parametrize('action', ['upload_photos', 'photo', 'delete_photo'])
def test_photos_require_ownership(records, action):
    owner, other, dream = records
    photo = DreamPhoto.objects.create(dream=dream, image=image_file())
    kwargs = {'id': dream.pk}
    if action != 'upload_photos':
        kwargs['photo_id'] = photo.pk
    with pytest.raises(Http404):
        getattr(DreamView(), action)(request_for(other, 'get' if action == 'photo' else 'post'), **kwargs)
    assert dream.photos.count() == 1


def test_photo_cannot_be_accessed_under_another_dream(records):
    owner, _, dream = records
    photo = DreamPhoto.objects.create(dream=dream, image=image_file())
    another = Dream.objects.create(user=owner, description='Outro sonho')
    with pytest.raises(Http404):
        DreamView().photo(request_for(owner, 'get'), another.pk, photo.pk)


def test_owner_can_read_photo(records):
    owner, _, dream = records
    photo = DreamPhoto.objects.create(dream=dream, image=image_file())
    response = DreamView().photo(request_for(owner, 'get'), dream.pk, photo.pk)
    assert response.status_code == 200
    assert response['Content-Type'] == 'image/png'
    assert response['Cache-Control'] == 'private, no-store'
    assert b''.join(response.streaming_content) == image_file().read()
    response.close()


@pytest.mark.parametrize('delete_dream', [False, True])
def test_deleting_photo_or_dream_removes_file_after_commit(records, django_capture_on_commit_callbacks, delete_dream):
    owner, _, dream = records
    photo = DreamPhoto.objects.create(dream=dream, image=image_file())
    storage, name = photo.image.storage, photo.image.name
    with django_capture_on_commit_callbacks(execute=True):
        if delete_dream:
            dream.delete()
        else:
            response = DreamView().delete_photo(request_for(owner), dream.pk, photo.pk)
            assert response.status_code == 302
        assert storage.exists(name)
    assert not storage.exists(name)
    assert not DreamPhoto.objects.filter(pk=photo.pk).exists()


@pytest.mark.parametrize('action', ['upload_photos', 'delete_photo'])
def test_photo_mutations_reject_get_requests(records, action):
    owner, _, dream = records
    kwargs = {'id': dream.pk}
    if action == 'delete_photo':
        kwargs['photo_id'] = 1
    assert getattr(DreamView(), action)(request_for(owner, 'get'), **kwargs).status_code == 405


def test_anonymous_cannot_access_photos(records):
    request = request_for(AnonymousUser(), 'get')
    response = DreamView().photo(request, records[2].pk, 1)
    assert response.status_code == 302
    assert '/login/' in response.url


def test_failed_database_save_cleans_up_uploaded_files(records, monkeypatch):
    owner, _, dream = records
    original_save = DreamPhoto.save

    def fail_second_save(instance, *args, **kwargs):
        original_save(instance, *args, **kwargs)
        if dream.photos.count() == 2:
            raise RuntimeError('Failed batch')

    monkeypatch.setattr(DreamPhoto, 'save', fail_second_save)
    with pytest.raises(RuntimeError, match='Failed batch'):
        DreamView().upload_photos(
            request_for(owner, data={'photos': [image_file(), image_file()]}),
            dream.pk,
        )
    assert not dream.photos.exists()
    assert not list(Path(dream.photos.model._meta.get_field('image').storage.location).rglob('*.png'))


def test_reorder_photos_persists_and_new_uploads_are_appended(records):
    owner, _, dream = records
    photos = [DreamPhoto.objects.create(dream=dream, image=image_file()) for _ in range(3)]
    photo_ids = [photos[2].pk, photos[0].pk, photos[1].pk]
    response = DreamView().reorder_photos(request_for(owner, data={'photo_ids': photo_ids}), dream.pk)
    assert response.status_code == 200
    assert list(dream.photos.values_list('pk', flat=True)) == photo_ids
    DreamView().upload_photos(request_for(owner, data={'photos': [image_file()]}), dream.pk)
    ordered = list(dream.photos.values_list('pk', flat=True))
    assert ordered[:3] == photo_ids
    assert ordered[3] not in photo_ids


@pytest.mark.parametrize('invalid_order', ['duplicate', 'missing', 'foreign', 'invalid'])
def test_invalid_photo_order_does_not_change_photos(records, invalid_order):
    owner, other, dream = records
    photos = [DreamPhoto.objects.create(dream=dream, image=image_file(), position=index) for index in range(2)]
    foreign_dream = Dream.objects.create(user=other, description='Outro sonho')
    foreign = DreamPhoto.objects.create(dream=foreign_dream, image=image_file())
    photo_ids = {
        'duplicate': [photos[0].pk, photos[0].pk],
        'missing': [photos[0].pk],
        'foreign': [photos[0].pk, foreign.pk],
        'invalid': ['invalid', photos[0].pk],
    }[invalid_order]
    response = DreamView().reorder_photos(request_for(owner, data={'photo_ids': photo_ids}), dream.pk)
    assert response.status_code == 400
    assert list(dream.photos.values_list('pk', flat=True)) == [photo.pk for photo in photos]


def test_only_owner_can_reorder_photos_using_post(records):
    owner, other, dream = records
    photo = DreamPhoto.objects.create(dream=dream, image=image_file())
    with pytest.raises(Http404):
        DreamView().reorder_photos(request_for(other, data={'photo_ids': [photo.pk]}), dream.pk)
    assert DreamView().reorder_photos(request_for(owner, 'get'), dream.pk).status_code == 405
