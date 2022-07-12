from rest_framework import serializers

from balanco.models import Categoria


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['tipo', 'cor', 'descricao', 'usuario']
