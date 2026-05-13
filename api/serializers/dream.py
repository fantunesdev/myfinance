from rest_framework import serializers

from api.serializers.base_serializer import BaseSerializer
from statement.models import Dream


class DreamSerializer(BaseSerializer):
    """Serializer para o modelo Dream."""

    current_value = serializers.SerializerMethodField()
    remaining_value = serializers.SerializerMethodField()
    progress_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Dream
        fields = [
            'id',
            'description',
            'target_value',
            'limit_date',
            'status',
            'current_value',
            'remaining_value',
            'progress_percentage',
            'user',
        ]
        read_only_fields = ['id', 'user', 'current_value', 'remaining_value', 'progress_percentage']

    def get_current_value(self, obj):
        """Retorna o valor total das transações associadas."""
        return obj.current_value

    def get_remaining_value(self, obj):
        """Retorna o valor faltante para atingir o objetivo."""
        return obj.remaining_value

    def get_progress_percentage(self, obj):
        """Retorna o percentual de progresso formatado."""
        return round(obj.progress_percentage, 2)
