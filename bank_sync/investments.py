"""Read current positions, never infer financial transactions from balance deltas."""
import hashlib
import json
import uuid
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from bank_sync.models import BankConnection, ExternalInvestment, InvestmentSnapshot, InvestmentSyncRun
from bank_sync.services import configured_reader
from clients.pluggy.reader import ProbeError
from investments.events import investment_atomic
from investments.models import Investment, InvestmentTransaction
from investments.services.transaction import InvestmentTransactionService
from investments.services.investment import InvestmentService

FIELDS = ('name', 'type', 'subtype', 'status', 'currencyCode', 'balance', 'amount', 'taxes', 'taxes2', 'quantity', 'value', 'date', 'purchaseDate', 'dueDate')


def normalize(raw):
    facts = {key: raw.get(key) for key in FIELDS}
    try:
        uuid.UUID(str(raw['id']))
        for key in ('balance', 'quantity'):
            number = Decimal(str(facts[key]))
            if not number.is_finite() or number < 0 or number >= Decimal('1000000000000'):
                raise ValueError()
            facts[key] = str(number)
        reference = parse_datetime(facts['date'])
        if reference is None or timezone.is_naive(reference):
            raise ValueError()
        if facts['status'] == 'TOTAL_WITHDRAWAL' and Decimal(facts['balance']) != 0:
            raise ValueError()
    except (KeyError, TypeError, ValueError, InvalidOperation):
        raise ProbeError('Posição inválida; a carteira anterior foi preservada.') from None
    return facts, reference


def ready(item):
    expires = parse_datetime(item.get('consentExpiresAt') or '')
    warnings = item.get('statusDetail') or {}
    investments = warnings.get('investments') or {}
    if (item.get('status') != 'UPDATED' or item.get('executionStatus') != 'SUCCESS'
            or (expires and expires <= timezone.now())
            or investments.get('error')):
        raise ProbeError('Conexão sem atualização completa de investimentos. Confira a autorização no Meu Pluggy.')


def sync_investments(connection, reader=None):
    token = uuid.uuid4()
    now = timezone.now()
    acquired = BankConnection.objects.filter(pk=connection.pk).filter(
        Q(lease_until__isnull=True) | Q(lease_until__lt=now)
    ).update(lease_token=token, lease_until=now + timedelta(minutes=5))
    if not acquired:
        raise ValidationError('Esta conexão já está sendo consultada. Aguarde.')
    run = InvestmentSyncRun.objects.create(connection=connection)
    try:
        reader = reader or configured_reader()
        reader.authenticate()
        item = reader.request('/items/' + str(connection.item_id))
        ready(item)
        rows = reader.numbered('/investments', {'itemId': str(connection.item_id), 'pageSize': 500})
        normalized = [(str(uuid.UUID(row['id'])), *normalize(row)) for row in rows]
        end = reader.request('/items/' + str(connection.item_id))
        ready(end)
        if end.get('lastUpdatedAt') != item.get('lastUpdatedAt'):
            raise ProbeError('A conexão mudou durante a coleta. Tente novamente.')
        result = {'checked': len(rows), 'updated': 0, 'unchanged': 0, 'pending': 0,
                  'source_updated_at': item.get('lastUpdatedAt')}
        with investment_atomic():
            locked = BankConnection.objects.select_for_update().get(pk=connection.pk)
            if locked.lease_token != token or locked.lease_until <= timezone.now():
                raise ProbeError('Consulta expirou; nenhum lote parcial foi aplicado.')
            InvestmentTransactionService.lock_user(connection.user)
            wallet = InvestmentTransactionService.get_default_wallet(connection.user)
            if wallet and InvestmentService.get_position(wallet)['value'] > 0:
                raise ValidationError('Há valores no caixa ainda sem alocação. Concilie os aportes antes de atualizar as posições para evitar dupla contagem.')
            for external_id, facts, reference in normalized:
                ext, _ = ExternalInvestment.objects.get_or_create(connection=connection, external_id=external_id)
                if ext.reference_at and reference < ext.reference_at:
                    result['unchanged'] += 1
                    continue
                if ext.investment_id is None:
                    # One-time bootstrap from exact IDs written by the audited reconciliation.
                    candidates = list(Investment.objects.filter(user=connection.user, notes__contains=external_id))
                    if len(candidates) == 1 and not ExternalInvestment.objects.filter(investment=candidates[0]).exists():
                        ext.investment = candidates[0]
                if ext.investment_id and ext.investment.user_id != connection.user_id:
                    raise ValidationError('Vínculo de proprietário inválido.')
                if not ext.investment_id or facts['currencyCode'] != 'BRL' or facts['status'] not in ('ACTIVE', 'TOTAL_WITHDRAWAL'):
                    ext.facts = facts
                    ext.save()
                    result['pending'] += 1
                    continue
                fingerprint = hashlib.sha256(json.dumps(facts, sort_keys=True).encode()).hexdigest()
                latest = ext.snapshots.order_by('-reference_at', '-id').first()
                if latest and latest.reference_at == reference and latest.fingerprint == fingerprint:
                    result['unchanged'] += 1
                    continue
                inv = ext.investment
                last_date = inv.transactions.order_by('-date', '-id').values_list('date', flat=True).first()
                effective = max(reference.date(), last_date) if last_date else reference.date()
                movement = InvestmentTransaction(user=connection.user, investment=inv, type='atualizacao',
                    date=effective, current_value=Decimal(facts['balance']), quantity=Decimal(facts['quantity']),
                    notes='Posição Pluggy; referência ' + reference.isoformat() + '. Não representa aporte, resgate ou rendimento realizado.')
                movement.full_clean()
                movement.save()
                snapshot, _ = InvestmentSnapshot.objects.get_or_create(external=ext, reference_at=reference,
                    fingerprint=fingerprint, defaults={'facts': facts, 'movement': movement})
                if snapshot.movement_id != movement.pk:
                    raise ProbeError('Revisão repetida da fonte; revisão manual necessária.')
                inv.status = 'closed' if facts['status'] == 'TOTAL_WITHDRAWAL' else 'active'
                if facts['dueDate']:
                    inv.due_date = timezone.datetime.fromisoformat(facts['dueDate'].replace('Z', '+00:00')).date()
                inv.save(update_fields=['status', 'due_date'])
                ext.facts, ext.reference_at = facts, reference
                ext.save()
                result['updated'] += 1
            run.state, run.finished_at, run.summary = 'succeeded', timezone.now(), result
            run.save()
        return result
    except Exception as error:
        run.state, run.finished_at = 'failed', timezone.now()
        run.message = str(error)[:255] if isinstance(error, (ValidationError, ProbeError)) else 'Consulta falhou; lote não aplicado.'
        run.save(update_fields=['state', 'finished_at', 'message'])
        raise
    finally:
        BankConnection.objects.filter(pk=connection.pk, lease_token=token).update(lease_until=None, lease_token=None)
