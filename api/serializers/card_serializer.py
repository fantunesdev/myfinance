from rest_framework import serializers

from balanco.models import Cartao


class CardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cartao
        fields = '__all__'
