from rest_framework import serializers

from statement.models import Category


class CategorySerializer(serializers.ModelSerializer):
    """
    Serializador para a classe Category.
    """

    class Meta:
        """
        Classe aninhada que fornece configurações adicionais para o serializador.
        """

        model = Category
        fields = '__all__'
