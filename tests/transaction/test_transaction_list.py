from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace

import pytest
from django.template import Context, Engine
from django.test import override_settings
from django.utils import translation


class TransactionRows(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == 'tr' and 'data-tx-id' in attributes:
            self.rows.append(attributes)


class Transactions(list):
    def exists(self):
        return bool(self)


@pytest.mark.parametrize('grouped', [False, True])
@override_settings(USE_THOUSAND_SEPARATOR=True)
def test_transaction_rows_expose_type_chart_policy_and_unlocalized_values(mocker, grouped):
    source = (Path(__file__).parents[2] / 'statement/templates/transaction/list.html').read_text()
    engine = Engine(
        loaders=[('django.template.loaders.locmem.Loader', {
            'index.html': '{% block content %}{% endblock %}',
            'transaction/list.html': source,
            'transaction/elements/invoice/invoice_navigation.html': '',
            'transaction/elements/invoice/invoice_dashboard.html': '',
        })],
        libraries={
            'static': 'django.templatetags.static',
            'l10n': 'django.templatetags.l10n',
            'custom_filters': 'statement.templatetags.custom_filters',
        },
    )
    mocker.patch('django.template.defaulttags.URLNode.render', return_value='/test/')
    transactions = Transactions([
        SimpleNamespace(id=1, value=1234.56, type='saida', installments_number=0, description='Aplicação'),
        SimpleNamespace(id=2, value=5000, type='entrada', installments_number=0, description='Salário'),
    ])
    for transaction in transactions:
        transaction.currency = SimpleNamespace(symbol='R$')
    context = Context({
        'request': SimpleNamespace(path='/fatura/' if grouped else '/pesquisa/'),
        'instances': transactions,
        'grouped_instances': [{'transactions': transactions, 'label': 'Cartão', 'total': 6234.56}] if grouped else [],
        'dashboard_excluded_transaction_ids': {1},
    })

    with translation.override('pt-br'):
        html = engine.get_template('transaction/list.html').render(context)

    parser = TransactionRows()
    parser.feed(html)
    assert len(parser.rows) == 2
    assert parser.rows[0]['data-value'] == '1234.56'
    assert parser.rows[0]['data-type'] == 'saida'
    assert parser.rows[0]['data-show-in-cashflow'] == 'false'
    assert parser.rows[1]['data-type'] == 'entrada'
    assert parser.rows[1]['data-show-in-cashflow'] == 'true'
