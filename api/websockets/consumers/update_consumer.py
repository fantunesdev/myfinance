from channels.generic.websocket import AsyncJsonWebsocketConsumer


class UpdateConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        """
        Aceita a conexão WebSocket e adiciona o cliente a um grupo.
        """
        await self.channel_layer.group_add("updates", self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        """
        Remove o cliente do grupo ao desconectar.
        """
        await self.channel_layer.group_discard('updates', self.channel_name)

    async def send_websocket_update(self, event):  # Alterado o nome
        """
        Envia a mensagem para os clientes conectados.
        """
        await self.send(text_data=event)
