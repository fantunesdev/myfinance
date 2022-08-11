from rest_framework import serializers

from balanco.models import Movimentacao


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movimentacao
        fields = '__all__'
