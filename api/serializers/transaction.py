from api.serializers.base_serializer import BaseSerializer
from statement.models import Transaction

class TransactionSerializer(BaseSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'