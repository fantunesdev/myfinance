import pytest
from django.test import RequestFactory
from django.http import Http404

from login.models import User
from statement.models import Category, Dream, Loan
from statement.services.core.category import CategoryService
from statement.views.core.category import CategoryView
from statement.views.dream.dream import DreamView
from statement.views.loan.loan import LoanView


@pytest.fixture
def users(db):
    owner = User.objects.create(username='owner', email='owner@test.invalid')
    other = User.objects.create(username='other', email='other@test.invalid')
    return owner, other


@pytest.mark.parametrize('model,view_class', [(Dream, DreamView), (Loan, LoanView)])
@pytest.mark.parametrize('action', ['update', 'delete'])
@pytest.mark.parametrize('method', ['get', 'post'])
def test_private_record_cannot_be_edited_or_deleted_by_another_user(users, model, view_class, action, method):
    owner, other = users
    instance = model.objects.create(user=owner, description='Original')
    request = getattr(RequestFactory(), method)('/record/', {'description': 'Changed', 'status': 'active'})
    request.user = other
    view = view_class()
    view.redirect_url = '/done/'

    with pytest.raises(Http404):
        getattr(view, action)(request, instance.pk)

    instance.refresh_from_db()
    assert instance.description == 'Original'
    assert instance.user_id == owner.pk


@pytest.mark.parametrize('model,view_class', [(Dream, DreamView), (Loan, LoanView)])
@pytest.mark.parametrize('action', ['update', 'delete'])
def test_owner_can_edit_and_delete_private_record(users, model, view_class, action):
    owner, _ = users
    instance = model.objects.create(user=owner, description='Original')
    request = RequestFactory().post('/record/', {
        'description': 'Changed', 'status': 'active', 'target_value': '100',
    })
    request.user = owner
    view = view_class()
    view.redirect_url = '/done/'

    response = getattr(view, action)(request, instance.pk)

    assert response.status_code == 302
    if action == 'delete':
        assert not model.objects.filter(pk=instance.pk).exists()
    else:
        instance.refresh_from_db()
        assert instance.description == 'Changed'
        assert instance.user_id == owner.pk


@pytest.mark.parametrize('action', ['update', 'delete'])
def test_staff_can_edit_and_delete_global_record_without_owner(users, monkeypatch, action):
    owner, _ = users
    owner.is_staff = True
    instance = Category.objects.create(description='Original', type='saida')
    request = RequestFactory().post('/record/', {'description': 'Changed', 'type': 'saida'})
    request.user = owner
    view = CategoryView()
    view.redirect_url = '/done/'
    # Category notifications are external to authorization and persistence.
    monkeypatch.setattr(CategoryService, 'send_category_update', lambda: None)

    response = getattr(view, action)(request, instance.pk)

    assert response.status_code == 302
    if action == 'delete':
        assert not Category.objects.filter(pk=instance.pk).exists()
    else:
        instance.refresh_from_db()
        assert instance.description == 'Changed'
