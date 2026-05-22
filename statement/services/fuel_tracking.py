from types import SimpleNamespace

from django.apps import apps


class FuelTrackingService:
    """Serviço que lê e grava a configuração de combustível no `login.Profile`."""

    @classmethod
    def _get_profile_model(cls):
        return apps.get_model('login', 'Profile')

    @classmethod
    def get(cls, user):
        Profile = cls._get_profile_model()
        try:
            profile = Profile.objects.get(user_id=user.id)
            return SimpleNamespace(
                active=profile.enable_fuel_tracking,
                subcategory=profile.fuel_subcategory,
                profile=profile,
            )
        except Profile.DoesNotExist:
            return None

    @classmethod
    def create(cls, user=None, active=False, subcategory=None):
        Profile = cls._get_profile_model()
        defaults = {
            'enable_fuel_tracking': active,
            'fuel_subcategory': subcategory,
        }
        profile, created = Profile.objects.get_or_create(user=user, defaults=defaults)
        if not created:
            profile.enable_fuel_tracking = defaults['enable_fuel_tracking']
            profile.fuel_subcategory = defaults['fuel_subcategory']
            profile.save(update_fields=['enable_fuel_tracking', 'fuel_subcategory'])
        return profile
