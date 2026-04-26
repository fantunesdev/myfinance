from rest_framework import serializers

from api.serializers.base_serializer import BaseSerializer
from statement.models import Transaction, Card, CardNumber, Category


class CardNumberSerializer(serializers.ModelSerializer):
    class Meta:
        model = CardNumber
        fields = '__all__'


class CardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Card
        fields = '__all__'


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class TransactionSerializer(BaseSerializer):
    card = serializers.SerializerMethodField()
    card_number = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = '__all__'

    def get_card(self, obj):
        """
        Retorna o card expandido apenas se 'expand' foi passado na query string,
        caso contrário retorna apenas o ID.
        """
        request = self.context.get('request')
        if request and 'card' in request.query_params.get('expand', '').split(','):
            return CardSerializer(obj.card).data if obj.card else None
        return obj.card_id

    def get_card_number(self, obj):
        """
        Retorna o card_number expandido apenas se 'expand' foi passado na query string,
        caso contrário retorna apenas o ID.
        """
        request = self.context.get('request')
        if request and 'card_number' in request.query_params.get('expand', '').split(','):
            return CardNumberSerializer(obj.card_number).data if obj.card_number else None
        return obj.card_number_id

    def get_category(self, obj):
        """
        Retorna a category expandida apenas se 'expand' foi passado na query string,
        caso contrário retorna apenas o ID.
        """
        request = self.context.get('request')
        if request and 'category' in request.query_params.get('expand', '').split(','):
            return CategorySerializer(obj.category).data if obj.category else None
        return obj.category_id
