from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from api.serializers.category_serializer import CategorySerializer
import json

SERIALIZERS = {
    'categories': CategorySerializer,
}

def send_websocket_update(entity_name, data):
    """
    Envia uma atualização via WebSocket para os clientes conectados.
    """
    # Define a classe usada dinamicamente
    serializer_class = SERIALIZERS.get(entity_name)
    if not serializer_class:
        raise ValueError(f'Serializer não definido para "{entity_name}"')

    # Serializa os dados de acordo com a entidade
    channel_layer = get_channel_layer()
    serialized_data = serializer_class(data, many=True).data

    # Envia a mensagem
    async_to_sync(channel_layer.group_send)(
        'updates',
        {
            'type': 'send_websocket_update',
            'data': {entity_name: serialized_data}
        }
    )
