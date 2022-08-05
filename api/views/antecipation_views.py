from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import antecipation_serializer
from balanco.services import antecipation_service


class AntecipationList(APIView):
    def get(self, request):
        antecipation = antecipation_service.read_atecipation_user(request.user)
        serializer = antecipation_serializer.AntecipationSerializer(antecipation)
        return Response(serializer.data, status=status.HTTP_200_OK)
