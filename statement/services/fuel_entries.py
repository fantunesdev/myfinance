"""Média histórica pelo hodômetro, sem médias de médias ou sobreposição."""
from decimal import Decimal
from datetime import date
from dateutil.relativedelta import relativedelta
from django.db.models import Q

from statement.models import FuelEntry


def mark_gap_after(transaction):
    """Excluir um abastecimento não pode fazer os litros faltantes parecerem completos."""
    if not FuelEntry.objects.filter(transaction=transaction).exists():
        return
    following = FuelEntry.objects.filter(transaction__user_id=transaction.user_id).filter(
        Q(transaction__posted_date__gt=transaction.posted_date) |
        Q(transaction__posted_date=transaction.posted_date, transaction_id__gt=transaction.pk)
    ).first()
    if following:
        following.break_before = True
        following.save(update_fields=['break_before'])


def fuel_history(user, exclude_transaction_id=None):
    entries = FuelEntry.objects.filter(transaction__user=user).select_related('transaction')
    if exclude_transaction_id:
        entries = entries.exclude(transaction_id=exclude_transaction_id)
    return [
        {
            'id': entry.transaction_id,
            'date': entry.transaction.posted_date.isoformat(),
            'liters': entry.liters,
            'amount': entry.amount_paid,
            'currency': entry.transaction.currency_id,
            'odometer': entry.odometer_km,
            'distance': entry.distance_km,
            'full_tank': entry.full_tank,
            'break_before': entry.break_before,
            'category_id': entry.transaction.category_id,
            'subcategory_id': entry.transaction.subcategory_id,
        }
        for entry in entries
    ]


def summarize_fuel(history):
    """Usa somente intervalos pelo hodômetro; a distância informada é individual."""
    periods = []
    excluded = []
    pending = []
    anchor = None
    current = None
    liters = Decimal('0')
    amount = Decimal('0')
    currencies = set()
    last_odometer = None

    for entry in history:
        odometer = entry['odometer']
        closed = entry['full_tank'] is True and odometer is not None
        broken = entry['break_before'] or (anchor is not None and (
            not entry['liters'] or (odometer is not None and last_odometer is not None and odometer <= last_odometer)
        ))
        if broken:
            excluded.extend({**item, 'reason': 'Intervalo interrompido ou dados inconsistentes.'} for item in pending)
            anchor = None
            current = None
            pending = []
            liters = amount = Decimal('0')
            currencies = set()
            last_odometer = None

        if odometer is not None:
            last_odometer = odometer

        if anchor is None:
            if closed:
                anchor = entry
            else:
                excluded.append({**entry, 'reason': 'Sem referência inicial de tanque cheio e hodômetro.'})
            continue

        pending.append(entry)
        liters += entry['liters']
        amount += entry['amount']
        currencies.add(entry['currency'])
        if not closed:
            continue

        distance = odometer - anchor['odometer']
        if current is None:
            current = {
                'start': anchor['date'], 'end': entry['date'],
                'distance': distance, 'liters': liters, 'amount': amount,
                'currencies': set(currencies), 'refuelings': len(pending),
                'source': 'odometer',
            }
            periods.append(current)
        else:
            current['end'] = entry['date']
            current['distance'] += distance
            current['liters'] += liters
            current['amount'] += amount
            current['currencies'].update(currencies)
            current['refuelings'] += len(pending)
        anchor = entry
        pending = []
        liters = amount = Decimal('0')
        currencies = set()

    for period in periods:
        period['consumption'] = period['distance'] / period['liters']
        period['currency'] = next(iter(period['currencies'])) if len(period['currencies']) == 1 else None
        period['cost_per_km'] = period['amount'] / period['distance'] if period['currency'] else None
        period['days'] = (date.fromisoformat(period['end']) - date.fromisoformat(period['start'])).days
        duration = relativedelta(date.fromisoformat(period['end']), date.fromisoformat(period['start']))
        months = duration.years * 12 + duration.months
        parts = []
        if months:
            parts.append(f'{months} ' + ('mês' if months == 1 else 'meses'))
        if duration.days or not parts:
            parts.append(f'{duration.days} ' + ('dia' if duration.days == 1 else 'dias'))
        period['duration'] = ' e '.join(parts)
        del period['currencies']

    total_distance = sum((p['distance'] for p in periods), Decimal('0'))
    total_liters = sum((p['liters'] for p in periods), Decimal('0'))
    total_amount = sum((p['amount'] for p in periods), Decimal('0'))
    currencies = {p['currency'] for p in periods}
    currency = next(iter(currencies)) if len(currencies) == 1 and None not in currencies else None
    return {
        'periods': periods,
        'distance': total_distance,
        'liters': total_liters,
        'consumption': total_distance / total_liters if total_liters else None,
        'cost_per_km': total_amount / total_distance if total_distance and currency else None,
        'price_per_liter': total_amount / total_liters if total_liters and currency else None,
        'currency': currency,
        'days': sum(p['days'] for p in periods),
        'start': min(p['start'] for p in periods) if periods else None,
        'end': max(p['end'] for p in periods) if periods else None,
        'pending': [{**e, 'reason': 'Aguardando tanque cheio com hodômetro para fechar o intervalo.'}
                    for e in pending],
        'excluded': excluded,
        'category_ids': sorted({e['category_id'] for e in history}),
        'subcategory_ids': sorted({e['subcategory_id'] for e in history}),
    }
