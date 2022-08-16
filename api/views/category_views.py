from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import category_serializer
from api.services import category_services
from balanco.services import categoria_service


class CategoryList(APIView):
    def get(self, request):
        categories = category_services.get_categories(request.user)
        serializer = category_serializer.CategorySerializer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CategoryDetails(APIView):
    def get(self, request, category_id):
        category = category_services.get_category_by_id(category_id, request.user)
        serializer = category_serializer.CategorySerializer(category)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CategoryType(APIView):
    def get(self, request, type):
        categories = category_services.get_categories_by_type(type, request.user)
        serializer = category_serializer.CategorySerializer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
