from django.urls import reverse

from login.models import Profile, User
from statement.models import Category, Subcategory, SubcategoryChartConfig
from statement.services.core.subcategory import SubcategoryService


def test_profile_links_to_personal_subcategory_preferences(authenticated_web):
    response = authenticated_web.client.get(reverse('get_profile'))
    assert response.status_code == 200
    assert reverse('edit_subcategory_preferences') in response.content.decode()


def test_preferences_save_only_for_current_user_and_keep_chart_flags(authenticated_web):
    category = Category.objects.create(description='Lazer', type='saida')
    travel = Subcategory.objects.create(description='Viagens', category=category)
    other = User.objects.create_user(username='other-pref', email='other@pref.invalid', name='Other')
    other_profile = Profile.objects.create(user=other)
    config = SubcategoryChartConfig.objects.create(user=authenticated_web.user, subcategory=travel)
    route = reverse('edit_subcategory_preferences')
    client = authenticated_web.client
    assert client.get(route).context['selected'] == []
    response = client.post(route, {'hidden_subcategories': [travel.pk]})
    assert response.status_code == 302
    assert response.url == reverse('get_profile')
    assert list(Profile.objects.get(user=authenticated_web.user).disabled_subcategories.all()) == [travel]
    assert not other_profile.disabled_subcategories.exists()
    assert not SubcategoryService.available_for_entry(authenticated_web.user).exists()
    assert list(SubcategoryService.available_for_entry(other)) == [travel]
    config.refresh_from_db()
    assert config.show_in_monthly_cashflow_donut is True
    assert client.get(route).context['selected'][0].subcategory == travel
    # An empty selection re-enables everything.
    assert client.post(route, {}).status_code == 302
    assert list(SubcategoryService.available_for_entry(authenticated_web.user)) == [travel]


def test_invalid_preference_does_not_clear_existing_selection(authenticated_web):
    category = Category.objects.create(description='Lazer')
    travel = Subcategory.objects.create(description='Viagens', category=category)
    profile = Profile.objects.get(user=authenticated_web.user)
    profile.disabled_subcategories.add(travel)
    response = authenticated_web.client.post(
        reverse('edit_subcategory_preferences'),
        {'hidden_subcategories': ['999999']},
    )
    assert response.status_code == 200
    assert response.context['form'].errors
    assert list(profile.disabled_subcategories.all()) == [travel]


def test_preferences_require_login(authenticated_web):
    authenticated_web.client.logout()
    route = reverse('edit_subcategory_preferences')
    assert authenticated_web.client.get(route).status_code == 302
    assert authenticated_web.client.post(route, {}).status_code == 302
