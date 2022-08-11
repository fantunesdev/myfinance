from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import card_serializer
from api.services import card_services


class CardList(APIView):
    def get(self, request):
        cards = card_services.get_cards(request.user)
        serializer = card_serializer.CardSerializer(cards, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CardDetails(APIView):
    def get(self, request, card_id):
        card = card_services.get_card_id(card_id, request.user)
        serializer = card_serializer.CardSerializer(card)
        return Response(serializer.data, status=status.HTTP_200_OK)
