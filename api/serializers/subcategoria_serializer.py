from rest_framework import serializers

from api.serializers.categoria_serializer import CategoriaSerializer
from balanco.models import Subcategoria


class SubcategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subcategoria
        fields = ['id', 'descricao', 'categoria']
