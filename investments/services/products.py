"""Institution products group custody lots; dated valuations never create money flows."""

from collections import defaultdict
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.utils import timezone

from investments.events import investment_atomic
from investments.models import InvestmentProduct, ProductValuation
from investments.services.transaction import InvestmentTransactionService


def assign_product(investment, facts):
    """Only explicit, evidenced contract rules can attach newly imported lots."""

    def equal(actual, expected):
        if isinstance(expected, list):
            return any(equal(actual, candidate) for candidate in expected)
        if actual is None or expected is None:
            return actual is expected
        try:
            return Decimal(str(actual)) == Decimal(str(expected))
        except InvalidOperation:
            return str(actual) == str(expected)

    matches = [
        product
        for product in InvestmentProduct.objects.filter(
            user=investment.user,
            broker=investment.broker,
            asset_type=investment.asset.asset_type,
        )
        if product.source_rules and all(equal(facts.get(key), value) for key, value in product.source_rules.items())
    ]
    if len(matches) > 1:
        raise ValidationError('Mais de um produto corresponde ao novo lote; revise as regras de agrupamento.')
    if matches:
        investment.product = matches[0]
        investment.full_clean()
        investment.save(update_fields=['product'])
    return investment.product


@investment_atomic()
def record_valuation(user, product, *, date, value, basis, source, evidence, reference_key):
    InvestmentTransactionService.lock_user(user)
    product = InvestmentProduct.objects.select_for_update().get(pk=product.pk, user=user)
    if date > timezone.localdate():
        raise ValidationError('A avaliação não pode estar no futuro.')
    existing = ProductValuation.objects.filter(product=product, reference_key=reference_key).first()
    if existing:
        if (existing.date, existing.value, existing.basis, existing.source, existing.evidence) != (
            date,
            Decimal(str(value)),
            basis,
            source,
            evidence,
        ):
            raise ValidationError('A referência já possui outra avaliação. Registre uma nova revisão.')
        return existing
    valuation = ProductValuation(
        product=product,
        date=date,
        value=value,
        basis=basis,
        source=source,
        evidence=evidence,
        reference_key=reference_key,
    )
    valuation.full_clean()
    valuation.save()
    return valuation


def assessed_product_value(lots, valuation, as_of=None):
    """Project a dated aggregate through cashflows without inventing lot quotes.

    Sales consume the valuation bridge in proportion to the documented units
    or principal redeemed. An internal transfer carries its bridge to the
    destination lot. Provider-only zeroing never withdraws money.
    """
    from investments.services.investment import InvestmentService

    openings = [InvestmentService.get_position(p['investment'], as_of=valuation.date) for p in lots]
    baseline = sum((p['value'] for p in openings), Decimal(0))
    bridge = valuation.value - baseline
    states, movements = {}, []
    for position, opening in zip(lots, openings):
        investment = position['investment']
        weight = opening['value'] / baseline if baseline else Decimal(1) / len(lots)
        states[investment.pk] = {
            'quantity': opening['quantity'],
            'principal': opening['remaining_principal'],
            'value': opening['value'],
            'bridge': bridge * weight,
        }
        movements.extend(
            m
            for m in investment.transactions.all()
            if m.user_id == investment.user_id and m.date > valuation.date and (as_of is None or m.date <= as_of)
        )
    # Recognize only an explicit, balanced operation wholly inside this product.
    operations = defaultdict(list)
    for movement in movements:
        if movement.type not in ('aporte', 'resgate'):
            continue
        if movement.operation_id:
            operations[('operation', movement.operation_id)].append(movement)
        else:
            for operation in movement.reconciled_operations.filter(kind='transfer', state__in=['applied', 'linked']):
                operations[('custody', operation.pk)].append(movement)
    destinations = {}
    for members in operations.values():
        if (
            len(members) == 2
            and {m.type for m in members} == {'aporte', 'resgate'}
            and members[0].date == members[1].date
            and members[0].amount == members[1].amount
            and members[0].investment_id != members[1].investment_id
        ):
            debit = next(m for m in members if m.type == 'resgate')
            credit = next(m for m in members if m.type == 'aporte')
            destinations[debit.pk] = credit.investment_id
    for movement in sorted(movements, key=lambda m: (m.date, m.pk)):
        state = states[movement.investment_id]
        if movement.type == 'resgate':
            cost = movement.redemption_principal if movement.redemption_principal is not None else movement.amount
            if movement.quantity and state['quantity'] > 0:
                fraction = min(movement.quantity / state['quantity'], Decimal(1))
            elif state['principal'] > 0:
                fraction = min(cost / state['principal'], Decimal(1))
            else:
                raise ValidationError('Concilie o custo ou a quantidade do resgate antes de projetar a avaliação.')
            consumed = state['bridge'] * fraction
            state['bridge'] -= consumed
            if movement.pk in destinations:
                states[destinations[movement.pk]]['bridge'] += consumed
            state['principal'] -= cost
            state['quantity'] -= movement.quantity or Decimal(0)
        elif movement.type == 'aporte':
            state['principal'] += movement.amount
            state['quantity'] += movement.quantity or Decimal(0)
        elif movement.type == 'atualizacao' and movement.quantity and movement.quantity > 0:
            state['quantity'] = movement.quantity
        state['value'] = InvestmentService.apply_value(state['value'], movement)
    return sum((state['value'] + state['bridge'] for state in states.values()), Decimal(0)).quantize(Decimal('0.01'))


def display_positions(user, positions):
    """Product assessment + ledger changes after its civil reference date.

    Lots retain individual source facts and prices. An aggregate bank assessment
    is never allocated back as invented individual asset quotes.
    """

    products = {p.pk: p for p in InvestmentProduct.objects.filter(user=user).prefetch_related('valuations')}
    grouped = defaultdict(list)
    result = []
    for position in positions:
        product_id = position['investment'].product_id
        if product_id not in products:
            result.append(position)
        else:
            grouped[product_id].append(position)
    for product_id, lots in grouped.items():
        product = products[product_id]
        if any(p['broker'].pk != product.broker_id or p['asset_type'] != product.asset_type for p in lots):
            raise ValidationError('O agrupamento contém lotes de outra instituição ou categoria.')
        position = dict(lots[0])
        for key in (
            'value',
            'invested',
            'income',
            'costs',
            'withdrawn',
            'quantity',
            'remaining_principal',
            'unwithdrawn_income',
        ):
            position[key] = sum((p[key] for p in lots), Decimal(0))
        valuations = [v for v in product.valuations.all() if v.date <= timezone.localdate()]
        valuation = max(valuations, key=lambda v: (v.date, v.pk)) if valuations else None
        if product.valuation_policy == 'institution' and valuation:
            position['value'] = assessed_product_value(lots, valuation)
        position.update(product=product, lots=lots, valuation=valuation, label=product.description)
        result.append(position)
    return result


def ensure_unclassified_opening_is_not_already_assessed(user, broker, asset_type, when):
    if ProductValuation.objects.filter(
        product__user=user,
        product__broker=broker,
        product__asset_type=asset_type,
        product__valuation_policy='institution',
        date__gte=when,
    ).exists():
        raise ValidationError(
            'A posição pode estar incluída em um saldo consolidado já conferido. Vincule o lote ao produto antes de registrar uma abertura histórica.'
        )
