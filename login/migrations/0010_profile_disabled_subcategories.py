from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('login', '0009_user_email_confirmation_nonce_and_more'),
        ('statement', '0027_retire_legacy_portfolio'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='disabled_subcategories',
            field=models.ManyToManyField(
                blank=True,
                related_name='disabled_by_profiles',
                to='statement.subcategory',
            ),
        ),
    ]
