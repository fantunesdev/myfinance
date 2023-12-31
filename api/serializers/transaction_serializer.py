from rest_framework import serializers

from statement.models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'


class TransactionsImportSerializer(serializers.Serializer):
        arquivo = serializers.FileField()
        account = serializers.IntegerField(required=False)
        card = serializers.IntegerField(required=False)