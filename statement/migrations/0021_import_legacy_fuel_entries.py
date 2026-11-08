"""Preserva as observações e importa apenas fatos reconhecíveis do bloco antigo."""
import re
from decimal import Decimal, InvalidOperation

from django.db import migrations
from django.db.models import Q


BLOCK = re.compile(r'#{5,}[ \t]*CÁLCULOS DE COMBUSTÍVEL[ \t]*#{5,}(.*?)#{5,}', re.S | re.I)


def read_number(block, label):
    match = re.search(rf'^\s*{label}:\s*(?:R\$\s*)?([0-9][0-9.,]*)', block, re.M | re.I)
    if not match:
        return None
    raw = match.group(1).rstrip('.,')
    if ',' in raw:
        raw = raw.replace('.', '').replace(',', '.')
    try:
        value = Decimal(raw)
        return value if value.is_finite() else None
    except InvalidOperation:
        return None


def import_entries(apps, schema_editor):
    Transaction = apps.get_model('statement', 'Transaction')
    FuelEntry = apps.get_model('statement', 'FuelEntry')
    alias = schema_editor.connection.alias
    transactions = Transaction.objects.using(alias).filter(
        type='saida', observation__icontains='CÁLCULOS DE COMBUSTÍVEL', value__gt=0,
    ).filter(Q(installment__isnull=True) | Q(paid=1)).order_by('pk')
    for transaction in transactions.iterator(chunk_size=500):
        blocks = BLOCK.findall(transaction.observation or '')
        # Blocos múltiplos/ambíguos ficam intactos para revisão manual.
        if len(blocks) != 1:
            continue
        block = blocks[0]
        liters = read_number(block, 'LITROS')
        distance = read_number(block, 'DISTÂNCIA')
        odometer = read_number(block, 'QUILOMETRAGEM')
        liters = liters if liters and 0 < liters < Decimal('10000000') else None
        distance = distance if distance and 0 < distance < Decimal('1000000000') else None
        odometer = odometer if odometer is not None and 0 <= odometer < Decimal('1000000000') else None
        if liters is None and distance is None and odometer is None:
            continue
        amount = Decimal(str(transaction.value))
        if transaction.installment_id:
            amount *= max(transaction.installments_number, 1)
        amount = amount.quantize(Decimal('0.01'))
        if amount <= 0 or amount >= Decimal('10000000000'):
            continue
        FuelEntry.objects.using(alias).get_or_create(transaction_id=transaction.pk, defaults={
            'liters': liters, 'distance_km': distance, 'odometer_km': odometer,
            'amount_paid': amount, 'full_tank': None, 'break_before': False,
        })


class Migration(migrations.Migration):
    dependencies = [('statement', '0020_fuelentry')]
    operations = [migrations.RunPython(import_entries, migrations.RunPython.noop)]
