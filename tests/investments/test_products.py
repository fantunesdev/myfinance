from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase
from django.urls import reverse

from bank_sync.investments import sync_investments
from bank_sync.models import BankConnection, ExternalInvestment, InvestmentSnapshot
from investments.models import Asset, Broker, Investment, InvestmentProduct, InvestmentTransaction, ProductValuation
from investments.services.dashboard import dashboard_payload
from investments.services.investment import InvestmentService
from investments.services.products import assign_product, record_valuation
from investments.views.product import product_detail
from login.models import User
from tests.pluggy.test_investment_sync import Reader


class ProductTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='products', email='products@test.invalid')
        self.other = User.objects.create(username='private', email='private@test.invalid')
        self.broker = Broker.objects.create(user=self.user, description='Inter')
        self.asset = Asset.objects.create(user=self.user, description='CDB', asset_type='fixed_income')
        self.product = InvestmentProduct.objects.create(
            user=self.user,
            broker=self.broker,
            asset_type='fixed_income',
            description='CDB liquidez diária',
            key='daily',
            source_rules={'type': 'FIXED_INCOME', 'subtype': 'CDB', 'rate': 102, 'rateType': 'CDI'},
            evidence='Agrupamento conferido pelo proprietário no aplicativo da instituição.',
        )
        self.lots = []
        for index, value in enumerate((100, 200)):
            lot = Investment.objects.create(
                user=self.user,
                broker=self.broker,
                asset=self.asset,
                product=self.product,
                description=f'Lote {index}',
                start_date=date(2026, 1, 1),
            )
            InvestmentTransaction.objects.create(
                user=self.user, investment=lot, date=date(2026, 1, 1), type='aporte', amount=value, quantity=value
            )
            self.lots.append(lot)

    def assess(self, value='330', key='bank-report'):
        return record_valuation(
            self.user,
            self.product,
            date=date(2026, 2, 1),
            value=Decimal(value),
            basis='gross',
            source='Inter — informado pelo proprietário',
            evidence='Saldo conferido no app do banco.',
            reference_key=key,
        )

    def test_groups_explicit_lots_without_merging_transactions_or_allocating_quotes(self):
        self.assess()
        payload = dashboard_payload(self.user, 'revision')
        self.assertEqual(len(payload['positions']), 1)
        self.assertEqual(payload['positions'][0]['label'], 'CDB liquidez diária')
        self.assertEqual(payload['positions'][0]['lot_count'], 2)
        self.assertEqual(payload['positions'][0]['value'], '330.00')
        self.assertIn('/produtos/', payload['positions'][0]['url'])
        self.assertEqual(InvestmentService.get_position(self.lots[0])['value'], 100)
        self.assertEqual(InvestmentTransaction.objects.count(), 2)
        self.assertEqual(payload['totals']['net_income'], '0')

    def test_real_later_flows_change_assessment_and_chart_matches_total(self):
        self.assess()
        InvestmentTransaction.objects.create(
            user=self.user, investment=self.lots[0], type='aporte', amount=50, date=date(2026, 2, 2)
        )
        payload = dashboard_payload(self.user, 'revision')
        self.assertEqual(Decimal(payload['totals']['total']), Decimal(380))
        curve = payload['progression_datasets'][0]
        self.assertEqual(curve['values'], [300, 330, 380])
        self.assertEqual(curve['valuation_adjustments'], [0, 30, 0])

    def test_late_history_already_in_assessed_date_does_not_duplicate_patrimony(self):
        self.assess()
        InvestmentTransaction.objects.create(
            user=self.user, investment=self.lots[0], type='aporte', amount=50, date=date(2026, 1, 15)
        )
        payload = dashboard_payload(self.user, 'revision')
        self.assertEqual(Decimal(payload['totals']['total']), Decimal(330))
        self.assertEqual(payload['progression_datasets'][0]['values'][-1], 330)

    def test_provider_zeroing_is_evidence_only_and_does_not_erase_assessed_product(self):
        self.assess()
        connection = BankConnection.objects.create(user=self.user, item_id=uuid4(), valuation_policy='institution')
        external = ExternalInvestment.objects.create(
            connection=connection, external_id=uuid4(), investment=self.lots[0]
        )
        row = {
            'id': str(external.external_id),
            'name': 'CDB',
            'status': 'TOTAL_WITHDRAWAL',
            'currencyCode': 'BRL',
            'date': '2026-03-01T03:00:00Z',
            'quantity': 0,
            'balance': 0,
        }
        sync_investments(connection, Reader([row]))
        snapshot = InvestmentSnapshot.objects.get()
        self.assertFalse(snapshot.movement.affects_value)
        self.lots[0].refresh_from_db()
        self.assertEqual(self.lots[0].status, 'active')
        self.assertEqual(InvestmentService.get_dashboard(self.user)['total'], 330)
        self.assertEqual(InvestmentService.get_position(self.lots[0])['quantity'], 0)

    def test_new_unclassified_lot_on_independent_connection_cannot_restore_provider_balance(self):
        self.lots[0].product = None
        self.lots[0].save()
        connection = BankConnection.objects.create(user=self.user, item_id=uuid4(), valuation_policy='institution')
        external = ExternalInvestment.objects.create(
            connection=connection, external_id=uuid4(), investment=self.lots[0]
        )
        self.assertFalse(external.investment.accepts_pluggy_value)
        row = {
            'id': str(external.external_id),
            'name': 'CDB',
            'status': 'ACTIVE',
            'currencyCode': 'BRL',
            'date': '2026-03-01T03:00:00Z',
            'quantity': 100,
            'balance': 5000,
        }
        sync_investments(connection, Reader([row]))
        self.assertEqual(InvestmentService.get_position(self.lots[0])['value'], 100)

    def test_rules_match_contract_terms_and_refuse_ambiguous_or_different_lots(self):
        lot = self.lots[0]
        lot.product = None
        lot.save()
        self.assertIsNone(
            assign_product(lot, {'type': 'FIXED_INCOME', 'subtype': 'CDB', 'rate': 100, 'rateType': 'CDI'})
        )
        self.assertEqual(
            assign_product(lot, {'type': 'FIXED_INCOME', 'subtype': 'CDB', 'rate': '102.0', 'rateType': 'CDI'}),
            self.product,
        )
        InvestmentProduct.objects.create(
            user=self.user,
            broker=self.broker,
            asset_type='fixed_income',
            description='Conflito',
            key='conflict',
            source_rules=self.product.source_rules,
            evidence='Outra regra.',
        )
        with self.assertRaises(ValidationError):
            assign_product(lot, {'type': 'FIXED_INCOME', 'subtype': 'CDB', 'rate': 102, 'rateType': 'CDI'})

    def test_assessment_is_idempotent_and_conflicting_reference_is_rejected(self):
        self.assess()
        self.assess()
        self.assertEqual(ProductValuation.objects.count(), 1)
        with self.assertRaises(ValidationError):
            self.assess(value='340')
        self.assertEqual(ProductValuation.objects.get().value, 330)

    def test_foreign_group_cannot_take_lot_or_be_read(self):
        other_broker = Broker.objects.create(user=self.other, description='Inter')
        foreign = InvestmentProduct.objects.create(
            user=self.other,
            broker=other_broker,
            asset_type='fixed_income',
            description='Private',
            key='private',
            evidence='Private',
        )
        self.lots[0].product = foreign
        with self.assertRaises(ValidationError):
            self.lots[0].full_clean()
        request = RequestFactory().get('/')
        request.user = self.user
        from django.http import Http404

        with self.assertRaises(Http404):
            product_detail(request, foreign.pk)

    def plan(self):
        for lot in self.lots:
            lot.product = None
            lot.save(update_fields=['product'])
        return {
            'user_id': self.user.pk,
            'connection_id': BankConnection.objects.create(user=self.user, item_id=uuid4()).pk,
            'batch_key': 'approved-preview',
            'date': '2026-02-01',
            'source': 'Inter',
            'evidence': 'Saldo conferido.',
            'expected_state_sha256': '',
            'products': [
                {
                    'key': 'reviewed-product',
                    'description': 'CDB conferido',
                    'broker_id': self.broker.pk,
                    'asset_type': 'fixed_income',
                    'value': '330',
                    'investment_ids': [lot.pk for lot in self.lots],
                }
            ],
            'expected_by_type': {'Renda fixa': '330'},
        }

    def test_plan_preview_rolls_back_and_apply_preserves_flows_and_is_idempotent(self):
        from investments.services.institution_reconciliation import apply_plan, financial_state, state_fingerprint

        plan = self.plan()
        before = financial_state(self.user)
        plan['expected_state_sha256'] = state_fingerprint(before)
        preview = apply_plan(self.user, plan, dry_run=True)
        self.assertEqual(financial_state(self.user), before)
        self.assertEqual(preview['after']['total'], '330.00')
        applied = apply_plan(self.user, plan, dry_run=False)
        self.assertTrue(applied['prior_movements_unchanged'])
        self.assertEqual(InvestmentTransaction.objects.count(), 2)
        self.assertTrue(apply_plan(self.user, plan, dry_run=False)['already_applied'])

    def test_plan_refuses_stale_state_and_wrong_expected_total_atomically(self):
        from investments.services.institution_reconciliation import apply_plan, financial_state, state_fingerprint

        plan = self.plan()
        before = financial_state(self.user)
        plan['expected_state_sha256'] = 'stale'
        with self.assertRaises(ValidationError):
            apply_plan(self.user, plan, dry_run=False)
        self.assertEqual(financial_state(self.user), before)
        plan['expected_state_sha256'] = state_fingerprint(before)
        plan['expected_by_type']['Renda fixa'] = '999'
        with self.assertRaises(ValidationError):
            apply_plan(self.user, plan, dry_run=False)
        self.assertEqual(financial_state(self.user), before)

    def test_command_simulates_applies_and_rejects_conflicting_input(self):
        import io
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from django.core.management import call_command
        from django.core.management.base import CommandError

        from investments.services.institution_reconciliation import financial_state, state_fingerprint

        plan = self.plan()
        plan['expected_state_sha256'] = state_fingerprint(financial_state(self.user))
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'plan.json'
            path.write_text(json.dumps(plan))
            output = io.StringIO()
            call_command('reconcile_institution_portfolio', path, stdout=output)
            self.assertTrue(json.loads(output.getvalue())['dry_run'])
            self.assertFalse(ProductValuation.objects.exists())
            call_command('reconcile_institution_portfolio', path, apply=True, stdout=io.StringIO())
            self.assertEqual(ProductValuation.objects.count(), 1)
            plan['products'][0]['value'] = '350'
            path.write_text(json.dumps(plan))
            with self.assertRaises(CommandError):
                call_command('reconcile_institution_portfolio', path, apply=True, stdout=io.StringIO())

    def test_plan_adds_unmapped_and_manual_positions_and_reclassifies_exterior_without_money_flows(self):
        from investments.services.institution_reconciliation import apply_plan, financial_state, state_fingerprint

        plan = self.plan()
        connection = BankConnection.objects.get(pk=plan['connection_id'])
        external = ExternalInvestment.objects.create(
            connection=connection,
            external_id=uuid4(),
            facts={
                'name': 'CDB',
                'status': 'ACTIVE',
                'currencyCode': 'BRL',
                'balance': '50',
                'quantity': '5000',
                'purchaseDate': '2026-01-15T03:00:00Z',
                'dueDate': '2027-01-15T03:00:00Z',
            },
        )
        plan['products'][0]['external_ids'] = [str(external.external_id)]
        global_asset = Asset.objects.create(user=self.user, description='Remessas', asset_type='other')
        global_lot = Investment.objects.create(
            user=self.user,
            broker=self.broker,
            asset=global_asset,
            description='Conta global',
            start_date=date(2026, 1, 1),
        )
        InvestmentTransaction.objects.create(
            user=self.user, investment=global_lot, type='aporte', amount=80, date=date(2026, 1, 1)
        )
        plan['products'] += [
            {
                'key': 'lig',
                'description': 'LIG',
                'broker_id': self.broker.pk,
                'asset_type': 'fixed_income',
                'value': '55',
                'new_lot': {'description': 'LIG sem histórico', 'asset_description': 'LIG'},
            },
            {
                'key': 'global',
                'description': 'Conta Global',
                'broker_id': self.broker.pk,
                'asset_type': 'international',
                'value': '90',
                'basis': 'reported',
                'investment_ids': [global_lot.pk],
                'reclassify_asset': True,
            },
        ]
        plan['expected_by_type'] = {'Renda fixa': '385', 'Exterior': '90'}
        plan['expected_state_sha256'] = state_fingerprint(financial_state(self.user))
        result = apply_plan(self.user, plan, dry_run=False)
        self.assertEqual(result['after']['total'], '475.00')
        self.assertTrue(result['prior_movements_unchanged'])
        self.assertEqual(InvestmentTransaction.objects.count(), 4)
        self.assertFalse(InvestmentTransaction.objects.order_by('-pk').first().affects_value)
        external.refresh_from_db()
        self.assertIsNotNone(external.investment_id)
        global_asset.refresh_from_db()
        self.assertEqual(global_asset.asset_type, 'international')
        self.assertTrue(apply_plan(self.user, plan, dry_run=False)['already_applied'])

    def test_product_and_valuation_validate_ownership_evidence_and_policy(self):
        from investments.models import ProductValuation

        foreign_broker = Broker.objects.create(user=self.other, description='Private bank')
        self.product.broker = foreign_broker
        with self.assertRaises(ValidationError):
            self.product.full_clean()
        self.product.broker = self.broker
        self.product.evidence = ''
        with self.assertRaises(ValidationError):
            self.product.full_clean()
        self.product.evidence = 'Conferido'
        self.product.source_rules = {'unknown': 'unsafe grouping'}
        with self.assertRaises(ValidationError):
            self.product.full_clean()
        self.product.source_rules = {}
        self.product.valuation_policy = 'pluggy'
        self.product.save()
        with self.assertRaises(ValidationError):
            self.assess()
        valuation = ProductValuation(
            product=self.product,
            date=date(2026, 2, 1),
            value=100,
            basis='gross',
            source='',
            evidence='',
            reference_key='invalid',
        )
        with self.assertRaises(ValidationError):
            valuation.full_clean()

    def test_unclassified_historical_opening_cannot_duplicate_a_confirmed_total(self):
        from investments.services.products import ensure_unclassified_opening_is_not_already_assessed

        self.assess()
        with self.assertRaises(ValidationError):
            ensure_unclassified_opening_is_not_already_assessed(
                self.user, self.broker, 'fixed_income', date(2026, 1, 1)
            )
        ensure_unclassified_opening_is_not_already_assessed(self.user, self.broker, 'fixed_income', date(2026, 2, 2))
        ensure_unclassified_opening_is_not_already_assessed(self.other, self.broker, 'fixed_income', date(2026, 1, 1))


@pytest.mark.django_db
def test_product_page_records_an_independent_assessment_and_lists_lots(authenticated_web):
    owner = authenticated_web.user
    broker = Broker.objects.create(user=owner, description='Banco do produto')
    product = InvestmentProduct.objects.create(
        user=owner,
        broker=broker,
        asset_type='fixed_income',
        key='web-product',
        description='CDB consolidado',
        evidence='Conferido no banco.',
    )
    asset = Asset.objects.create(user=owner, description='CDB web', asset_type='fixed_income')
    lot = Investment.objects.create(
        user=owner,
        broker=broker,
        asset=asset,
        product=product,
        description='Lote com vencimento próprio',
        start_date=date(2020, 1, 1),
    )
    InvestmentTransaction.objects.create(user=owner, investment=lot, type='aporte', amount=100, date=date(2020, 1, 1))
    url = reverse('detail_investment_product', args=[product.pk])
    response = authenticated_web.client.get(url)
    assert response.status_code == 200
    assert 'Lote com vencimento próprio' in response.content.decode()
    response = authenticated_web.client.post(
        url,
        {
            'date': '2026-02-01',
            'value': '120.50',
            'basis': 'gross',
            'source': 'Banco',
            'evidence': 'Saldo total conferido.',
            'reference_key': 'web-report',
        },
    )
    assert response.status_code == 302
    assert ProductValuation.objects.get(product=product).value == Decimal('120.50')
    assert InvestmentTransaction.objects.filter(investment=lot).count() == 1
    assert authenticated_web.client.get(url).status_code == 200
    response = authenticated_web.client.post(
        url,
        {
            'date': '2099-02-01',
            'value': '150',
            'basis': 'gross',
            'source': 'Banco',
            'evidence': 'Data inválida.',
            'reference_key': 'future-report',
        },
    )
    assert response.status_code == 200
    assert 'futuro' in response.content.decode()
    assert ProductValuation.objects.filter(product=product).count() == 1


@pytest.mark.django_db
def test_partial_and_full_redemptions_consume_the_independent_valuation_bridge():
    from investments.services.transaction import InvestmentTransactionService as Service

    owner = User.objects.create(username='redemption-product', email='redeem@test.invalid')
    broker = Broker.objects.create(user=owner, description='Inter')
    product = InvestmentProduct.objects.create(
        user=owner,
        broker=broker,
        asset_type='fixed_income',
        key='redeem',
        description='CDB',
        evidence='Saldo conferido',
    )
    asset = Asset.objects.create(user=owner, description='CDB', asset_type='fixed_income')
    lots = []
    for value in (100, 200):
        lot = Investment.objects.create(
            user=owner,
            broker=broker,
            asset=asset,
            product=product,
            description=f'Lote {value}',
            start_date=date(2026, 1, 1),
        )
        InvestmentTransaction.objects.create(
            user=owner, investment=lot, type='aporte', amount=value, date=date(2026, 1, 1), quantity=value
        )
        lots.append(lot)
    record_valuation(
        owner,
        product,
        date=date(2026, 2, 1),
        value=330,
        basis='gross',
        source='Inter',
        evidence='Saldo conferido',
        reference_key='closing',
    )
    Service.redeem_to_wallet(lots[0], gross_amount=60, principal_amount=50, quantity=50, date=date(2026, 2, 2))
    displayed = next(p for p in InvestmentService.get_dashboard(owner)['positions'] if p.get('product'))
    assert displayed['value'] == Decimal(275)
    Service.redeem_to_wallet(lots[0], gross_amount=60, principal_amount=50, quantity=50, date=date(2026, 2, 3))
    Service.redeem_to_wallet(lots[1], gross_amount=240, principal_amount=200, quantity=200, date=date(2026, 2, 3))
    dashboard = InvestmentService.get_dashboard(owner)
    displayed = next(p for p in dashboard['positions'] if p.get('product'))
    assert displayed['value'] == 0
    assert dashboard['total'] == 360
    assert sum(ds['values'][-1] for ds in dashboard['progression_datasets']) == 360


@pytest.mark.django_db
def test_internal_transfer_carries_the_valuation_to_its_destination_lot():
    from investments.services.transaction import InvestmentTransactionService as Service

    owner = User.objects.create(username='transfer-product', email='transfer@test.invalid')
    broker = Broker.objects.create(user=owner, description='Inter')
    product = InvestmentProduct.objects.create(
        user=owner,
        broker=broker,
        asset_type='fixed_income',
        key='transfer',
        description='CDB',
        evidence='Saldo conferido',
    )
    asset = Asset.objects.create(user=owner, description='CDB', asset_type='fixed_income')
    source = Investment.objects.create(
        user=owner, broker=broker, asset=asset, product=product, description='Origem', start_date=date(2026, 1, 1)
    )
    target = Investment.objects.create(
        user=owner, broker=broker, asset=asset, product=product, description='Destino', start_date=date(2026, 1, 1)
    )
    InvestmentTransaction.objects.create(
        user=owner, investment=source, type='aporte', amount=100, date=date(2026, 1, 1)
    )
    record_valuation(
        owner,
        product,
        date=date(2026, 2, 1),
        value=110,
        basis='gross',
        source='Inter',
        evidence='Saldo conferido',
        reference_key='closing',
    )
    Service.transfer_between_investments(source, target, 100, date=date(2026, 2, 2))
    assert InvestmentService.get_dashboard(owner)['total'] == 110
    Service.redeem_to_wallet(target, gross_amount=120, principal_amount=100, date=date(2026, 2, 3))
    dashboard = InvestmentService.get_dashboard(owner)
    assert next(p for p in dashboard['positions'] if p.get('product'))['value'] == 0
    assert dashboard['total'] == 120
    assert sum(ds['values'][-1] for ds in dashboard['progression_datasets']) == 120
