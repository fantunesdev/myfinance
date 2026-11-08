"""Mantém o formulário automático para quem já usava o bloco de combustível."""
import unicodedata

from django.db import migrations


def configure_tracking(apps, schema_editor):
    FuelEntry = apps.get_model('statement', 'FuelEntry')
    Profile = apps.get_model('login', 'Profile')
    alias = schema_editor.connection.alias
    candidates = {}
    rows = FuelEntry.objects.using(alias).values_list(
        'transaction__user_id', 'transaction__subcategory_id', 'transaction__subcategory__description',
    ).distinct()
    for user_id, subcategory_id, description in rows:
        candidates.setdefault(user_id, {})[subcategory_id] = description
    for user_id, subcategories in candidates.items():
        named = [pk for pk, description in subcategories.items() if
                 unicodedata.normalize('NFKD', description).encode('ascii', 'ignore').decode().strip().lower() == 'combustivel']
        selected = named[0] if len(named) == 1 else next(iter(subcategories)) if len(subcategories) == 1 else None
        if selected is None:
            continue
        profile, _ = Profile.objects.using(alias).get_or_create(user_id=user_id)
        # Uma configuração explícita, inclusive desativada, continua sendo respeitada.
        if profile.fuel_subcategory_id is None:
            profile.fuel_subcategory_id = selected
            profile.enable_fuel_tracking = True
            profile.save(using=alias, update_fields=['fuel_subcategory', 'enable_fuel_tracking'])


class Migration(migrations.Migration):
    dependencies = [
        ('statement', '0021_import_legacy_fuel_entries'),
        ('login', '0005_profile_enable_fuel_tracking'),
    ]
    operations = [migrations.RunPython(configure_tracking, migrations.RunPython.noop)]
