from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from api.serializers import default_serializer
from api.services import default_services


class Defaults(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        defaults_data = default_services.get_defaults()
        serializer = default_serializer.DefaultsSerializer(defaults_data)
        return Response(serializer.data, status=status.HTTP_200_OK)