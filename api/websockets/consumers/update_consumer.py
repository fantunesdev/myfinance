from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from investments.events import dashboard_revision
from channels.db import database_sync_to_async


class UpdateConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return
        if not await self.security_allowed():
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
        if not await self.security_allowed():
            await self.close(code=4401)
            return
        # Existing shared category updates retain their original format.
        await self.send_json(event)

    async def investments_changed(self, event):
        if not await self.security_allowed():
            await self.close(code=4401)
            return
        await self.send_json(
            {'type': 'investments.changed', 'revision': event['revision']}
        )

    async def classifier_changed(self, event):
        if not await self.security_allowed():
            await self.close(code=4401)
            return
        await self.send_json({'type': 'classifier.changed', 'job': event['job']})


    async def security_changed(self, event):
        await self.close(code=4401)

    async def security_allowed(self):
        if self.scope.get('session') is None:
            return bool(self.scope.get('user') and not self.scope['user'].two_factor_enabled)
        return await self.session_security_allowed()

    @database_sync_to_async
    def session_security_allowed(self):
        from login.security import verified_websocket_session
        return verified_websocket_session(self.scope)
