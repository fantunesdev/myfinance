from decimal import Decimal

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


def link_existing_wallets_and_funding(apps, schema_editor):
    Investment = apps.get_model('investments', 'Investment')
    Movement = apps.get_model('investments', 'InvestmentTransaction')
    alias = schema_editor.connection.alias
    investments = Investment.objects.using(alias)
    movements = Movement.objects.using(alias)
    user_ids = investments.order_by().values_list('user_id', flat=True).distinct()
    for user_id in user_ids:
        candidates = list(
            investments.filter(user_id=user_id).filter(
                models.Q(description='Caixa de investimentos BRL') | models.Q(asset__symbol='CASH-BRL')
            )
        )
        # Do not guess which of several pre-existing wallets owns the history.
        if len(candidates) != 1:
            continue
        wallet = candidates[0]
        investments.filter(pk=wallet.pk).update(default_wallet_for_id=user_id)
        for funding in movements.filter(investment_id=wallet.pk, type='aporte', operation_id__isnull=False).iterator():
            group = list(movements.filter(operation_id=funding.operation_id, user_id=user_id))
            debits = [item for item in group if item.investment_id == wallet.pk and item.type == 'resgate']
            credits = [item for item in group if item.investment_id != wallet.pk and item.type == 'aporte']
            if len(group) == 3 and len(debits) == len(credits) == 1:
                movements.filter(pk=credits[0].pk).update(funding_transaction_id=funding.pk)
                movements.filter(pk=funding.pk).update(operation_id=None)
        for debit in (
            movements.filter(user_id=user_id, type='resgate', operation_id__isnull=False)
            .exclude(investment_id=wallet.pk)
            .iterator()
        ):
            group = list(movements.filter(operation_id=debit.operation_id, user_id=user_id))
            cash_credits = [item for item in group if item.investment_id == wallet.pk and item.type == 'aporte']
            earnings = [
                item
                for item in group
                if item.investment_id == debit.investment_id and item.type in ('rendimento', 'custo')
            ]
            if len(cash_credits) == 1 and len(group) == len(earnings) + 2 and earnings:
                result = sum(
                    (item.amount if item.type == 'rendimento' else -item.amount for item in earnings), Decimal('0')
                )
                principal = debit.amount - result
                if principal > 0:
                    movements.filter(pk=debit.pk).update(redemption_principal=principal)


class Migration(migrations.Migration):
    dependencies = [('investments', '0004_investmenttransaction_due_date')]
    operations = [
        migrations.AlterField(
            model_name='investmenttransaction',
            name='investment',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT, related_name='transactions', to='investments.investment'
            ),
        ),
        migrations.AddField(
            model_name='investment',
            name='default_wallet_for',
            field=models.OneToOneField(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='default_investment_wallet',
                to='login.user',
            ),
        ),
        migrations.AddField(
            model_name='investmenttransaction',
            name='funding_transaction',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='funded_transactions',
                to='investments.investmenttransaction',
            ),
        ),
        migrations.AddField(
            model_name='investmenttransaction',
            name='redemption_principal',
            field=models.DecimalField(blank=True, decimal_places=2, editable=False, max_digits=14, null=True),
        ),
        migrations.AlterField(
            model_name='investmenttransaction',
            name='amount',
            field=models.DecimalField(
                decimal_places=2, default=0, max_digits=14, validators=[django.core.validators.MinValueValidator(0)]
            ),
        ),
        migrations.AlterField(
            model_name='investmenttransaction',
            name='quantity',
            field=models.DecimalField(
                blank=True,
                decimal_places=8,
                max_digits=20,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal('0.00000001'))],
            ),
        ),
        migrations.AlterField(
            model_name='investmenttransaction',
            name='unit_price',
            field=models.DecimalField(
                blank=True,
                decimal_places=6,
                max_digits=14,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal('0.000001'))],
            ),
        ),
        migrations.AlterField(
            model_name='investmenttransaction',
            name='current_value',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=14,
                null=True,
                validators=[django.core.validators.MinValueValidator(0)],
            ),
        ),
        migrations.RunPython(link_existing_wallets_and_funding, migrations.RunPython.noop),
    ]
