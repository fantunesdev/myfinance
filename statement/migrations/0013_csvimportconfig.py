# Generated manually on 2026-08-30

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('statement', '0012_cardnumber_can_see_others'),
    ]

    operations = [
        migrations.CreateModel(
            name='CSVImportConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=80)),
                (
                    'target_model',
                    models.CharField(
                        choices=[
                            ('statement_transaction', 'Lançamento financeiro'),
                            ('investments_investmenttransaction', 'Movimentação de investimento'),
                        ],
                        default='statement_transaction',
                        max_length=40,
                    ),
                ),
                ('date_column', models.CharField(default='date', max_length=80)),
                ('description_column', models.CharField(default='title', max_length=80)),
                ('value_column', models.CharField(default='amount', max_length=80)),
                (
                    'payment_method',
                    models.IntegerField(choices=[(1, 'Cartão de Crédito'), (2, 'Conta Corrente')], default=2),
                ),
                ('matching_fields', models.JSONField(blank=True, default=list)),
                (
                    'account',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to='statement.account',
                    ),
                ),
                (
                    'card',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to='statement.card',
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.AddConstraint(
            model_name='csvimportconfig',
            constraint=models.UniqueConstraint(fields=('user', 'name'), name='unique_csv_import_config_name_by_user'),
        ),
    ]
