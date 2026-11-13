from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('login', '0005_profile_enable_fuel_tracking')]

    operations = [
        migrations.AddField(
            model_name='profile', name='inactivity_logout_enabled',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='profile', name='inactivity_logout_minutes',
            field=models.PositiveSmallIntegerField(
                default=10, validators=[MinValueValidator(1), MaxValueValidator(1440)],
            ),
        ),
    ]
