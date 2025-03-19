import json

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models import QuerySet

from api.serializers.category_serializer import CategorySerializer
from api.serializers.next_month_view_serializer import NextMonthViewSerializer

SERIALIZERS = {
    'categories': CategorySerializer,
    'next_month_view': NextMonthViewSerializer,
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
    has_many = isinstance(data, QuerySet)
    serialized_data = serializer_class(data, many=has_many).data

    # Cria e envia a mensagem
    message = {'type': 'send_websocket_update', 'data': {entity_name: serialized_data}}

    async_to_sync(channel_layer.group_send)('updates', message)
