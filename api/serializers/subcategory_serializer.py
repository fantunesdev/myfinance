from rest_framework import serializers

from balanco.models import Subcategoria


class SubcategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Subcategoria
        fields = '__all__'
