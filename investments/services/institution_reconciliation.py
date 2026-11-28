"""Audited import of owner-confirmed products and aggregate institution balances."""

import hashlib
import json
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.serializers import serialize
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.utils import timezone

from bank_sync.models import BankConnection, ExternalInvestment, InvestmentReconciliationBaseline, InvestmentSnapshot
from investments.events import investment_atomic
from investments.models import Asset, Broker, Investment, InvestmentProduct, InvestmentTransaction, ProductValuation
from investments.services.investment import InvestmentService
from investments.services.products import record_valuation
from investments.services.transaction import InvestmentTransactionService


def financial_state(user):
    rows = []
    for model in (
        Asset,
        Broker,
        Investment,
        InvestmentTransaction,
        BankConnection,
        ExternalInvestment,
        InvestmentSnapshot,
        InvestmentReconciliationBaseline,
    ):
        if model == ExternalInvestment:
            queryset = model.objects.filter(connection__user=user)
        elif model == InvestmentSnapshot:
            queryset = model.objects.filter(external__connection__user=user)
        elif model == InvestmentReconciliationBaseline:
            queryset = model.objects.filter(investment__user=user)
        else:
            queryset = model.objects.filter(user=user)
        items = json.loads(serialize('json', queryset.order_by('pk')))
        for item in items:
            # Stable across the additive schema migration and the preparation snapshot.
            if model == Investment:
                item['fields'].pop('product', None)
            if model == BankConnection:
                item['fields'].pop('valuation_policy', None)
        rows.extend(items)
    return rows


def state_fingerprint(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True, cls=DjangoJSONEncoder).encode()).hexdigest()


def summary(user):
    dashboard = InvestmentService.get_dashboard(user)
    return {
        'total': str(dashboard['total']),
        'by_type': {label: str(value) for label, value in dashboard['by_type']},
        'products': [
            {
                'label': p.get('label', str(p['investment'])),
                'value': str(p['value']),
                'lot_count': len(p.get('lots', [p])),
            }
            for p in dashboard['positions']
            if p['value']
        ],
    }


@investment_atomic()
def apply_plan(user, plan, *, dry_run=True):
    InvestmentTransactionService.lock_user(user)
    if plan.get('user_id') != user.pk or not plan.get('batch_key') or not plan.get('evidence'):
        raise ValidationError('O plano precisa identificar o proprietário, lote de auditoria e evidência.')
    when = date.fromisoformat(plan['date'])
    if when > timezone.localdate():
        raise ValidationError('A data do plano não pode estar no futuro.')
    specs = plan.get('products') or []
    if not specs or len({s['key'] for s in specs}) != len(specs):
        raise ValidationError('Produtos ausentes ou repetidos no plano.')
    existing = list(
        ProductValuation.objects.filter(product__user=user, reference_key=plan['batch_key']).select_related('product')
    )
    if existing:
        actual = {(v.product.key, v.value, v.date) for v in existing}
        expected = {(s['key'], Decimal(s['value']), when) for s in specs}
        if actual != expected:
            raise ValidationError('O lote já existe com produtos ou valores diferentes.')
        specs_by_key = {spec['key']: spec for spec in specs}
        for valuation in existing:
            spec = specs_by_key[valuation.product.key]
            product = valuation.product
            if (
                product.description != spec['description']
                or product.broker_id != spec['broker_id']
                or product.asset_type != spec['asset_type']
                or product.source_rules != spec.get('source_rules', {})
                or product.kind != spec.get('kind', 'product')
                or product.valuation_policy != 'institution'
                or valuation.basis != spec.get('basis', 'gross')
                or valuation.source != spec.get('source', plan['source'])
                or valuation.evidence != spec.get('evidence', plan['evidence'])
            ):
                raise ValidationError('O lote já existe com condições ou evidências diferentes.')
        if not BankConnection.objects.filter(
            pk=plan['connection_id'], user=user, valuation_policy='institution'
        ).exists():
            raise ValidationError('A política da conexão mudou após a conciliação.')
        return {'already_applied': True, 'dry_run': dry_run, 'after': summary(user)}
    before_state = financial_state(user)
    if state_fingerprint(before_state) != plan.get('expected_state_sha256'):
        raise ValidationError('A carteira ou a fonte mudou após a preparação. Refaça a prévia; nada foi aplicado.')
    connection = BankConnection.objects.select_for_update().get(pk=plan['connection_id'], user=user)
    before = summary(user)
    prior_movement_ids = set(InvestmentTransaction.objects.filter(user=user).values_list('pk', flat=True))
    connection.valuation_policy = 'institution'
    connection.save(update_fields=['valuation_policy'])
    used = set()
    for spec in specs:
        broker = Broker.objects.get(pk=spec['broker_id'], user=user)
        product, created = InvestmentProduct.objects.get_or_create(
            user=user,
            broker=broker,
            key=spec['key'],
            defaults={
                'description': spec['description'],
                'asset_type': spec['asset_type'],
                'kind': spec.get('kind', 'product'),
                'source_rules': spec.get('source_rules', {}),
                'valuation_policy': 'institution',
                'evidence': spec.get('evidence', plan['evidence']),
            },
        )
        if not created:
            raise ValidationError('Produto já existente fora deste lote de auditoria; prepare uma revisão explícita.')
        product.full_clean()
        lots = list(Investment.objects.filter(user=user, broker=broker, pk__in=spec.get('investment_ids', [])))
        if len(lots) != len(set(spec.get('investment_ids', []))):
            raise ValidationError('Lote local inexistente ou de outra instituição.')
        for external_id in spec.get('external_ids', []):
            ext = ExternalInvestment.objects.select_for_update().get(connection=connection, external_id=external_id)
            if ext.investment_id:
                lot = ext.investment
            else:
                facts = ext.facts
                if facts.get('status') != 'ACTIVE' or facts.get('currencyCode') != 'BRL':
                    raise ValidationError('Abertura de lote sem posição ativa em reais.')
                asset, _ = Asset.objects.get_or_create(
                    user=user,
                    description=str(facts['name']),
                    symbol='',
                    defaults={'asset_type': spec['asset_type'], 'currency': 'BRL'},
                )
                lot = Investment.objects.create(
                    user=user,
                    broker=broker,
                    asset=asset,
                    description=f'{facts["name"]} · {(facts.get("purchaseDate") or str(when))[:10]}',
                    start_date=date.fromisoformat((facts.get('purchaseDate') or str(when))[:10]),
                    due_date=date.fromisoformat(facts['dueDate'][:10]) if facts.get('dueDate') else None,
                    notes=f'{plan["batch_key"]}: lote recebido da fonte {ext.external_id}. Avaliação não equivale a aporte; histórico de compra continua sujeito à conciliação.',
                )
                ext.investment = lot
                ext.save(update_fields=['investment'])
                # Quantity evidence only: do not invent a purchase or its cash funding.
                quantity = InvestmentTransaction(
                    user=user,
                    investment=lot,
                    date=when,
                    type='atualizacao',
                    current_value=Decimal(str(facts['balance'])),
                    quantity=Decimal(str(facts['quantity'])),
                    affects_value=False,
                    notes=f'{plan["batch_key"]}: quantidade da fonte; saldo independente registrado no produto.',
                )
                quantity.full_clean()
                quantity.save()
            if lot.user_id != user.pk or lot.broker_id != broker.pk:
                raise ValidationError('Vínculo externo pertence a outro proprietário ou intermediário.')
            lots.append(lot)
        if spec.get('new_lot'):
            if lots:
                raise ValidationError('Um saldo novo não pode duplicar lotes já selecionados.')
            new = spec['new_lot']
            asset, _ = Asset.objects.get_or_create(
                user=user,
                description=new['asset_description'],
                symbol='',
                defaults={'asset_type': spec['asset_type'], 'currency': 'BRL'},
            )
            lots.append(
                Investment.objects.create(
                    user=user,
                    broker=broker,
                    asset=asset,
                    description=new['description'],
                    start_date=when,
                    notes=f'{plan["batch_key"]}: saldo informado pelo proprietário; aquisição e custo não foram fabricados.',
                )
            )
        if not lots:
            raise ValidationError('Produto sem lotes ou posição de abertura.')
        for lot in lots:
            if lot.pk in used:
                raise ValidationError('O mesmo lote não pode compor dois produtos.')
            used.add(lot.pk)
            if lot.product_id:
                raise ValidationError('Lote já agrupado; revisão explícita necessária.')
            if spec.get('reclassify_asset'):
                if lot.asset.investments.exclude(pk=lot.pk).exists():
                    raise ValidationError('A reclassificação afetaria outros investimentos.')
                lot.asset.asset_type = spec['asset_type']
                lot.asset.full_clean()
                lot.asset.save(update_fields=['asset_type'])
            lot.product = product
            lot.full_clean()
            lot.save(update_fields=['product'])
        record_valuation(
            user,
            product,
            date=when,
            value=Decimal(spec['value']),
            basis=spec.get('basis', 'gross'),
            source=spec.get('source', plan['source']),
            evidence=spec.get('evidence', plan['evidence']),
            reference_key=plan['batch_key'],
        )
    # Source movements, realized income, principal and wallet contributions are untouched.
    after_state = financial_state(user)
    original_movements = [row for row in before_state if row['model'] == 'investments.investmenttransaction']
    after_original = [
        row
        for row in after_state
        if row['model'] == 'investments.investmenttransaction' and row['pk'] in prior_movement_ids
    ]
    if original_movements != after_original:
        raise ValidationError('A correção alterou movimentos anteriores; lote revertido.')
    after = summary(user)
    for label, expected in plan.get('expected_by_type', {}).items():
        if Decimal(after['by_type'].get(label, '0')) != Decimal(expected):
            raise ValidationError('O total por categoria não corresponde à conferência; lote revertido.')
    report = {
        'already_applied': False,
        'dry_run': dry_run,
        'before': before,
        'after': after,
        'products_created': len(specs),
        'lots_assigned': len(used),
        'prior_movements_unchanged': True,
        'state_before_sha256': state_fingerprint(before_state),
        'state_after_sha256': state_fingerprint(after_state),
    }
    if dry_run:
        transaction.set_rollback(True)
    return report
