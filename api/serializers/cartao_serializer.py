from rest_framework import serializers

from balanco.models import Cartao


class CartaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cartao
        fields = '__all__'
