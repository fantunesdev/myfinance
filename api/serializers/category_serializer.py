from rest_framework import serializers

from balanco.models import Categoria


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = '__all__'
