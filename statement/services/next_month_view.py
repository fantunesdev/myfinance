from types import SimpleNamespace

from django.apps import apps


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
        """Return a wrapper with .first() for compatibility with older code."""

        class _Wrapper:
            def __init__(self, obj):
                self._obj = obj

            def first(self):
                return self._obj

        return _Wrapper(cls.get(user))

    @classmethod
    def create(cls, user=None, day=10, active=False):
        """Create or update profile fields for next month view and return the Profile."""
        Profile = cls._get_profile_model()
        defaults = {
            'next_month_day': day,
            'use_next_month': active,
        }
        profile, created = Profile.objects.get_or_create(user=user, defaults=defaults)
        if not created:
            profile.next_month_day = defaults['next_month_day']
            profile.use_next_month = defaults['use_next_month']
            profile.save()
        return profile
