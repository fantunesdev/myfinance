import json

from channels.generic.websocket import AsyncJsonWebsocketConsumer


class UpdateConsumer(AsyncJsonWebsocketConsumer):
    """
    Consumer responsável por gerenciar a comunicação WebSocket para enviar atualizações aos
    clientes conectados.
    """

    async def connect(self):
        """
        Aceita a conexão WebSocket e adiciona o cliente ao grupo "updates".
        """
        await self.channel_layer.group_add('updates', self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        """
        Remove o cliente do grupo ao desconectar.
        """
        await self.channel_layer.group_discard('updates', self.channel_name)

    async def send_websocket_update(self, event):  # Alterado o nome
        """
        Envia a atualização para os clientes conectados.
        """
        text_data = json.dumps(event)
        await self.send(text_data=text_data)
