from django.apps import apps
from types import SimpleNamespace
from datetime import date
from dateutil.relativedelta import relativedelta

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


class NextMonthViewService:
    """Serviço que lê e grava a configuração de Next Month View no `login.Profile`."""

    @classmethod
    def _get_profile_model(cls):
        return apps.get_model('login', 'Profile')

    @classmethod
    def get(cls, user):
        Profile = cls._get_profile_model()
        try:
            profile = Profile.objects.get(user_id=user.id)
            return SimpleNamespace(day=profile.next_month_day, active=profile.use_next_month, profile=profile)
        except Profile.DoesNotExist:
            return None

    @classmethod
    def get_all(cls, user):
        from django.apps import apps
        from types import SimpleNamespace


        class NextMonthViewService:
            """Serviço que lê e grava a configuração de Next Month View no `login.Profile`."""

            @classmethod
            def _get_profile_model(cls):
                return apps.get_model('login', 'Profile')

            @classmethod
            def get(cls, user):
                Profile = cls._get_profile_model()
                try:
                    p = Profile.objects.get(user_id=user.id)
                    return SimpleNamespace(day=p.next_month_day, active=p.use_next_month, profile=p)
                except Profile.DoesNotExist:
                    return None

            @classmethod
            def get_all(cls, user):
                class _Wrapper:
                    def __init__(self, obj):
                        self._obj = obj

                    def first(self):
                        return self._obj

                return _Wrapper(cls.get(user))

            @classmethod
            def create(cls, **kwargs):
                Profile = cls._get_profile_model()
                user = kwargs.get('user')
                defaults = {
                    'next_month_day': kwargs.get('day', 10),
                    'use_next_month': kwargs.get('active', False),
                }
                profile, created = Profile.objects.get_or_create(user=user, defaults=defaults)
                if not created:
                    profile.next_month_day = defaults['next_month_day']
                    profile.use_next_month = defaults['use_next_month']
                    profile.save()
                return profile
