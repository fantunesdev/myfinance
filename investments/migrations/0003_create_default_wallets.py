from django.db import migrations
from django.utils import timezone


DEFAULT_WALLET_BROKER_DESCRIPTION = 'Caixa de investimentos'
DEFAULT_WALLET_ASSET_DESCRIPTION = 'Disponível para investir'
DEFAULT_WALLET_ASSET_SYMBOL = 'CASH-BRL'
DEFAULT_WALLET_INVESTMENT_DESCRIPTION = 'Caixa de investimentos BRL'


def create_default_wallets(apps, schema_editor):
    User = apps.get_model('login', 'User')
    Broker = apps.get_model('investments', 'Broker')
    Asset = apps.get_model('investments', 'Asset')
    Investment = apps.get_model('investments', 'Investment')

    for user in User.objects.all().iterator():
        broker, _ = Broker.objects.get_or_create(
            description=DEFAULT_WALLET_BROKER_DESCRIPTION,
            user_id=user.id,
            defaults={'kind': 'wallet'},
        )
        asset, _ = Asset.objects.get_or_create(
            description=DEFAULT_WALLET_ASSET_DESCRIPTION,
            symbol=DEFAULT_WALLET_ASSET_SYMBOL,
            user_id=user.id,
            defaults={
                'asset_type': 'currency',
                'income_behavior': 'none',
                'currency': 'BRL',
            },
        )
        Investment.objects.get_or_create(
            description=DEFAULT_WALLET_INVESTMENT_DESCRIPTION,
            asset=asset,
            broker=broker,
            user_id=user.id,
            defaults={
                'start_date': timezone.localdate(),
                'status': 'active',
            },
        )


def remove_default_wallets(apps, schema_editor):
    Investment = apps.get_model('investments', 'Investment')

    Investment.objects.filter(
        description=DEFAULT_WALLET_INVESTMENT_DESCRIPTION,
        asset__symbol=DEFAULT_WALLET_ASSET_SYMBOL,
        broker__description=DEFAULT_WALLET_BROKER_DESCRIPTION,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('login', '0005_profile_enable_fuel_tracking'),
        ('investments', '0002_investmenttransaction_operation_id_and_more'),
    ]

    operations = [
        migrations.RunPython(create_default_wallets, remove_default_wallets),
    ]
