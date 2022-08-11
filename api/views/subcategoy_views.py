from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import subcategory_serializer
from api.services import subcategory_services


class SubcategoryList(APIView):
    def get(self, request):
        subcategories = subcategory_services.get_subcategories(request.user)
        serializer = subcategory_serializer.SubcategorySerializer(subcategories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SubcategoriesCategory(APIView):
    def get(self, request, category_id):
        subcategories = subcategory_services.get_subcategories_category(category_id, request.user)
        serializer = subcategory_serializer.SubcategorySerializer(subcategories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
