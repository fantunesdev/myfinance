from rest_framework import serializers

from api.serializers.base_serializer import BaseSerializer
from statement.models import Account, Bank, Transaction, Card, CardNumber, Category, Dream, Subcategory


class BankSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bank
        fields = '__all__'


class AccountSerializer(serializers.ModelSerializer):
    bank = BankSerializer()

    class Meta:
        model = Account
        fields = '__all__'


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


class SubcategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Subcategory
        fields = '__all__'


class DreamMinimalSerializer(serializers.ModelSerializer):
    """Serializer minimalista para Dream (para evitar recursão)."""
    class Meta:
        model = Dream
        fields = ['id', 'description', 'target_value', 'status']


class TransactionSerializer(BaseSerializer):
    account = serializers.SerializerMethodField()
    card = serializers.SerializerMethodField()
    card_number = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    subcategory = serializers.SerializerMethodField()
    dream = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = '__all__'

    def get_account(self, obj):
        """
        Retorna a account expandida apenas se 'expand' foi passado na query string,
        caso contrário retorna apenas o ID.
        """
        request = self.context.get('request')
        if request and 'account' in request.query_params.get('expand', '').split(','):
            return AccountSerializer(obj.account).data if obj.account else None
        return obj.account_id

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

    def get_subcategory(self, obj):
        """
        Retorna a subcategory expandida apenas se 'expand' foi passado na query string,
        caso contrário retorna apenas o ID.
        """
        request = self.context.get('request')
        if request and 'subcategory' in request.query_params.get('expand', '').split(','):
            return SubcategorySerializer(obj.subcategory).data if obj.subcategory else None
        return obj.subcategory_id

    def get_dream(self, obj):
        """
        Retorna o dream expandido apenas se 'expand' foi passado na query string,
        caso contrário retorna apenas o ID.
        """
        request = self.context.get('request')
        if request and 'dream' in request.query_params.get('expand', '').split(','):
            return DreamMinimalSerializer(obj.dream).data if obj.dream else None
        return obj.dream_id
