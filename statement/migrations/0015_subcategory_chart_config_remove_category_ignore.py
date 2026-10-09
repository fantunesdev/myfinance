from django.db import migrations, models
import django.db.models.deletion


CHART_FLAG_NAMES = (
    'show_in_monthly_cashflow_donut',
    'show_in_annual_statement',
    'show_in_monthly_expense_category_bar',
    'show_in_annual_expense_category_bar',
    'show_in_monthly_expense_line',
)


def migrate_chart_configs(apps, schema_editor):
    Subcategory = apps.get_model('statement', 'Subcategory')
    SubcategoryChartConfig = apps.get_model('statement', 'SubcategoryChartConfig')
    User = apps.get_model('login', 'User')

    Subcategory.objects.filter(id=54).update(is_investment=True)

    users = list(User.objects.all())
    subcategories = list(Subcategory.objects.select_related('category'))
    configs = []

    for user in users:
        for subcategory in subcategories:
            values = {flag_name: True for flag_name in CHART_FLAG_NAMES}

            if subcategory.category.ignore:
                values = {flag_name: False for flag_name in CHART_FLAG_NAMES}

            if subcategory.id == 54:
                values.update(
                    {
                        'show_in_monthly_cashflow_donut': True,
                        'show_in_annual_statement': True,
                        'show_in_monthly_expense_category_bar': False,
                        'show_in_annual_expense_category_bar': False,
                        'show_in_monthly_expense_line': False,
                    }
                )

            configs.append(SubcategoryChartConfig(user=user, subcategory=subcategory, **values))

    SubcategoryChartConfig.objects.bulk_create(configs, ignore_conflicts=True)


def reverse_chart_configs(apps, schema_editor):
    SubcategoryChartConfig = apps.get_model('statement', 'SubcategoryChartConfig')
    SubcategoryChartConfig.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('login', '0003_profile'),
        ('statement', '0014_csvimportconfig_installments'),
    ]

    operations = [
        migrations.CreateModel(
            name='SubcategoryChartConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('show_in_monthly_cashflow_donut', models.BooleanField(default=True)),
                ('show_in_annual_statement', models.BooleanField(default=True)),
                ('show_in_monthly_expense_category_bar', models.BooleanField(default=True)),
                ('show_in_annual_expense_category_bar', models.BooleanField(default=True)),
                ('show_in_monthly_expense_line', models.BooleanField(default=True)),
                (
                    'subcategory',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='chart_configs',
                        to='statement.subcategory',
                    ),
                ),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='login.user')),
            ],
        ),
        migrations.AddConstraint(
            model_name='subcategorychartconfig',
            constraint=models.UniqueConstraint(
                fields=('user', 'subcategory'),
                name='unique_subcategory_chart_config_by_user',
            ),
        ),
        migrations.RunPython(migrate_chart_configs, reverse_chart_configs),
        migrations.RemoveField(
            model_name='category',
            name='ignore',
        ),
    ]
