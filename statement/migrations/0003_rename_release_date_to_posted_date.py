from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statement', '0002_add_prepaid_field'),
    ]

    operations = [
        migrations.RenameField(
            model_name='transaction',
            old_name='release_date',
            new_name='posted_date',
        ),
    ]
