from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import next_month_view_serializer
from api.services import next_month_view_services


class NextMonthView(APIView):
    def get(self, request):
        next_month_view = next_month_view_services.get_next_month_view(
            request.user
        )
        serializer = next_month_view_serializer.NextMonthViewSerializer(
            next_month_view
        )
        return Response(serializer.data, status=status.HTTP_200_OK)
