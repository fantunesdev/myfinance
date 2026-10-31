import asyncio
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.test import RequestFactory, TestCase, override_settings
from django.urls import include, path
from rest_framework.test import APIRequestFactory, force_authenticate

from api.views.investment import InvestmentView
from api.websockets.consumers.update_consumer import UpdateConsumer
from investments.events import dashboard_revision
from investments.models import Asset, Investment, InvestmentTransaction
from investments.services.investment import InvestmentService
from investments.services.transaction import (
    InvestmentTransactionService as Service,
)
from investments.views.dashboard import InvestmentsDashboardView
from login.models import User

urlpatterns = [
    path(
        'api/investments/dashboard/',
        InvestmentView.as_view({'get': 'dashboard'}),
        name='investments-dashboard',
    ),
    path('investimentos/', include('investments.urls')),
]


@override_settings(
    ROOT_URLCONF=__name__,
    CHANNEL_LAYERS={
        'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}
    },
)
class InvestmentDashboardTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create(
            username='dashboard', email='dashboard@test.invalid'
        )
        self.other = User.objects.create(
            username='other', email='other@test.invalid'
        )
        self.wallet = Service.get_or_create_default_wallet(self.user)
        self.other_wallet = Service.get_or_create_default_wallet(self.other)
        asset = Asset.objects.create(
            description='CDB', asset_type='fixed_income', user=self.user
        )
        self.investment = Investment.objects.create(
            description='CDB DI',
            asset=asset,
            broker=self.wallet.broker,
            user=self.user,
            start_date=date(2026, 1, 1),
        )
        InvestmentTransaction.objects.create(
            investment=self.wallet,
            user=self.user,
            date=date(2026, 1, 1),
            type='aporte',
            amount=1000,
        )
        InvestmentTransaction.objects.create(
            investment=self.other_wallet,
            user=self.other,
            date=date(2026, 1, 1),
            type='aporte',
            amount=9999,
        )

    def get_dashboard(self, user=None, etag=None):
        headers = {'HTTP_IF_NONE_MATCH': etag} if etag else {}
        request = APIRequestFactory().get(
            '/api/investments/dashboard/', **headers
        )
        if user:
            force_authenticate(request, user=user)
        return InvestmentView.as_view({'get': 'dashboard'})(request)

    def test_endpoint_is_authenticated_and_scoped_to_owner(self):
        self.assertIn(self.get_dashboard().status_code, (401, 403))
        response = self.get_dashboard(self.user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['user_id'], self.user.pk)
        self.assertEqual(response.data['totals']['total'], '1000.00')
        self.assertEqual(
            response.data['totals']['available_to_invest'], '1000.00'
        )
        ids = {position['id'] for position in response.data['positions']}
        self.assertEqual(ids, {self.wallet.pk, self.investment.pk})
        self.assertNotIn(self.other_wallet.pk, ids)
        self.assertEqual(
            self.get_dashboard(self.other).data['totals']['total'], '9999.00'
        )
        response.render()

    def test_unchanged_revision_returns_304_without_portfolio_queries(self):
        first = self.get_dashboard(self.user)
        with patch(
            'api.views.investment.dashboard_payload',
            side_effect=AssertionError('aggregation must be skipped'),
        ):
            response = self.get_dashboard(self.user, first['ETag'])
        self.assertEqual(response.status_code, 304)
        self.assertIn('private', response['Cache-Control'])

    def test_page_only_renders_shell_without_aggregating_dashboard(self):
        request = RequestFactory().get(
            '/investimentos/?asset_type=fixed_income'
        )
        request.user = self.user
        with patch.object(
            InvestmentService,
            'get_dashboard',
            side_effect=AssertionError('duplicate query'),
        ), patch.object(
            InvestmentsDashboardView,
            '_render',
            side_effect=lambda r, f, t, context: context,
        ):
            context = InvestmentsDashboardView().dashboard(request)
        self.assertEqual(context['dashboard_config']['userId'], self.user.pk)
        self.assertEqual(
            context['dashboard_config']['apiUrl'],
            '/api/investments/dashboard/',
        )
        self.assertNotIn('positions', context)

    def test_complete_transfer_queues_one_notification_after_commit(self):
        with patch('investments.events.publish_changes') as publish:
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                Service.transfer_between_investments(
                    self.wallet, self.investment, 600, date=date(2026, 1, 2)
                )
                publish.assert_not_called()
            self.assertEqual(len(callbacks), 1)
            publish.assert_called_once_with((self.user.pk,))

    def test_failed_transfer_discards_notifications_and_financial_writes(self):
        with patch('investments.events.publish_changes') as publish:
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                with patch.object(
                    Service,
                    'validate_balances',
                    side_effect=ValidationError('failure'),
                ):
                    with self.assertRaises(ValidationError):
                        Service.transfer_between_investments(
                            self.wallet,
                            self.investment,
                            600,
                            date=date(2026, 1, 2),
                        )
            self.assertEqual(callbacks, [])
            publish.assert_not_called()
        self.assertEqual(
            InvestmentService.get_position(self.wallet)['value'],
            Decimal('1000'),
        )
        self.assertFalse(self.investment.transactions.exists())

    def test_mutation_advances_only_owner_revision_and_invalidates_etag(self):
        first = self.get_dashboard(self.user)
        other_revision = dashboard_revision(self.other.pk)
        with self.captureOnCommitCallbacks(execute=True):
            Service.transfer_between_investments(
                self.wallet, self.investment, 600, date=date(2026, 1, 2)
            )
        second = self.get_dashboard(self.user, first['ETag'])
        self.assertEqual(second.status_code, 200)
        self.assertNotEqual(first['ETag'], second['ETag'])
        self.assertEqual(dashboard_revision(self.other.pk), other_revision)

    def test_renaming_asset_also_invalidates_revision_after_commit(self):
        previous = dashboard_revision(self.user.pk)
        with self.captureOnCommitCallbacks(execute=True):
            self.investment.asset.description = 'Outro nome'
            self.investment.asset.save()
        self.assertNotEqual(dashboard_revision(self.user.pk), previous)

    def test_endpoint_retries_a_snapshot_changed_mid_read(self):
        with patch(
            'api.views.investment.dashboard_revision',
            side_effect=['a', 'b', 'b', 'b'],
        ):
            response = self.get_dashboard(self.user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['revision'], 'b')

    def test_socket_rejects_anonymous_and_isolates_private_events(self):
        async def scenario():
            anonymous = WebsocketCommunicator(UpdateConsumer.as_asgi(), '/ws/')
            anonymous.scope['user'] = AnonymousUser()
            connected, code = await anonymous.connect(timeout=5)
            self.assertFalse(connected)
            self.assertEqual(code, 4401)
            await anonymous.disconnect()
            clients = []
            try:
                for user in (self.user, self.other):
                    client = WebsocketCommunicator(
                        UpdateConsumer.as_asgi(), '/ws/'
                    )
                    client.scope['user'] = user
                    self.assertTrue((await client.connect(timeout=5))[0])
                    ready = await client.receive_json_from(timeout=5)
                    self.assertEqual(ready['type'], 'investments.ready')
                    clients.append(client)
                await get_channel_layer().group_send(
                    f'user_updates_{self.user.pk}',
                    {
                        'type': 'investments_changed',
                        'revision': 'new',
                    },
                )
                self.assertEqual(
                    await clients[0].receive_json_from(),
                    {'type': 'investments.changed', 'revision': 'new'},
                )
                self.assertTrue(await clients[1].receive_nothing(timeout=0.05))
                await get_channel_layer().group_send(
                    'updates',
                    {
                        'type': 'send_websocket_update',
                        'data': {'categories': []},
                    },
                )
                for client in clients:
                    self.assertEqual(
                        (await client.receive_json_from(timeout=5))['data'],
                        {'categories': []},
                    )
            finally:
                for client in clients:
                    await client.disconnect()

        asyncio.run(scenario())
