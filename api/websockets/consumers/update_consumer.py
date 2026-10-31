from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from investments.events import dashboard_revision


class UpdateConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return
        self.user_group = f'user_updates_{user.pk}'
        await self.channel_layer.group_add('updates', self.channel_name)
        await self.channel_layer.group_add(self.user_group, self.channel_name)
        await self.accept()
        revision = await sync_to_async(dashboard_revision)(user.pk)
        await self.send_json(
            {'type': 'investments.ready', 'revision': revision}
        )

    async def disconnect(self, code):
        if hasattr(self, 'user_group'):
            await self.channel_layer.group_discard(
                'updates', self.channel_name
            )
            await self.channel_layer.group_discard(
                self.user_group, self.channel_name
            )

    async def send_websocket_update(self, event):
        # Existing shared category updates retain their original format.
        await self.send_json(event)

    async def investments_changed(self, event):
        await self.send_json(
            {'type': 'investments.changed', 'revision': event['revision']}
        )
