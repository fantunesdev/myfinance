from rest_framework import serializers

from balanco.models import Movimentacao


class MovimentacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movimentacao
        fields = '__all__'
