from django.apps import apps


def create_next_year_view(user):
    Profile = apps.get_model('login', 'Profile')
    Profile.objects.get_or_create(user=user, defaults={'next_month_day': 1, 'use_next_month': False})
