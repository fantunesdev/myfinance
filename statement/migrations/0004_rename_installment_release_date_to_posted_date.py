from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statement', '0003_rename_release_date_to_posted_date'),
    ]

    operations = [
        migrations.RenameField(
            model_name='installment',
            old_name='release_date',
            new_name='posted_date',
        ),
    ]
