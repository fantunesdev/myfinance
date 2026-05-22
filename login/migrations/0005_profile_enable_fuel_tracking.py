from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('login', '0004_alter_profile_next_month_day'),
        ('statement', '0010_loan_notes'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='enable_fuel_tracking',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='profile',
            name='fuel_subcategory',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                to='statement.subcategory',
            ),
        ),
    ]
