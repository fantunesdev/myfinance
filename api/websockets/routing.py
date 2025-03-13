from django.urls import path

from api.websockets.consumers.update_consumer import UpdateConsumer

websocket_urlpatterns = [
    path('ws/', UpdateConsumer.as_asgi()),
]
