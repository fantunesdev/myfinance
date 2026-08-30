# Generated manually on 2026-08-30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('statement', '0013_csvimportconfig'),
    ]

    operations = [
        migrations.AddField(
            model_name='csvimportconfig',
            name='installment_column',
            field=models.CharField(blank=True, max_length=80, null=True),
        ),
        migrations.AddField(
            model_name='csvimportconfig',
            name='installment_format',
            field=models.CharField(
                choices=[('auto', 'Automático'), ('slash', 'x/y'), ('dash', 'x-y')],
                default='auto',
                max_length=10,
            ),
        ),
    ]
