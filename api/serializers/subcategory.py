from rest_framework import serializers

from statement.models import Subcategory


class SubcategorySerializer(serializers.ModelSerializer):
    """
    Serializador para o modelo Subcategory.
    """

    class Meta:
        """
        Classe aninhada que fornece configurações adicionais para o serializador.
        """

        model = Subcategory
        fields = '__all__'
