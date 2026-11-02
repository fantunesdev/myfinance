"""Match explicitly opted-in fixed expenses using original source identities."""
from django.db.models import Q

from statement.models import Transaction
from statement.utils.transaction_input import parse_amount, plain_text


def source_identity(data):
    merchant = data.get('merchant_description')
    if not merchant and data.get('source_type') == 'csv':
        merchant = data.get('original_description')
    return ' '.join(plain_text(merchant or '').split())


def object_id(value):
    return getattr(value, 'pk', value) or None


class FixedExpenseMatcher:
    def __init__(self, user, account=None, card=None):
        self.user_id = getattr(user, 'pk', None)
        self.account_id = object_id(account)
        self.card_id = object_id(card)
        self._rules = None

    def find(self, data):
        if data.get('source_type') not in ('csv', 'notification'):
            return None
        if data.get('event_type') in ('refund', 'card_payment') or data.get('type') == 'entrada':
            return None
        amount = parse_amount(data.get('value'))
        if amount is not None and amount < 0:
            return None
        identity = source_identity(data)
        if not identity or not self.user_id or not (self.card_id or self.account_id):
            return None
        if self._rules is None:
            rules = Transaction.objects.filter(
                user_id=self.user_id, fixed=True, event_type='fixed_expense', type='saida',
            )
            if self.card_id:
                rules = rules.filter(Q(card_id=self.card_id) | Q(card_number__card_id=self.card_id))
            else:
                rules = rules.filter(account_id=self.account_id, card__isnull=True, card_number__isnull=True)
            self._rules = list(rules.order_by('pk').values(
                'pk', 'merchant_description', 'original_description', 'source_type', 'source_app',
            ))
        for rule in self._rules:
            if rule['source_app'] and data.get('source_app') and rule['source_app'] != data['source_app']:
                continue
            if source_identity(rule) == identity:
                return rule['pk']
        return None

    def annotate(self, data):
        matched = self.find(data)
        if matched:
            data.update(
                ignored_fixed_expense=True, fixed_transaction_id=matched,
                event_type='fixed_expense', fixed=True,
                review_reason='Despesa fixa já cadastrada. Esta cobrança será ignorada na importação.',
            )
        return matched
