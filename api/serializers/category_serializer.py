from rest_framework import serializers

from statement.models import Category


class CategorySerializer(serializers.ModelSerializer):
    """
    Serializador para a classe Category.

    Este serializador converte instâncias da classe Category em dados serializados
    e vice-versa. Ele é usado para integrar objetos Category com o Django REST Framework.

    Attributes:
        model (Category): O modelo associado ao serializador.
        fields (str): Uma string indicando quais campos do modelo devem ser incluídos
                      na serialização. No caso, '__all__' significa todos os campos.

    """

    class Meta:
        """
        Classe aninhada que fornece configurações adicionais para o serializador.

        Attributes:
            model (Category): O modelo associado ao serializador. Neste caso, a classe Category.
            fields (str): Uma string indicando quais campos do modelo devem ser incluídos
                          na serialização. No caso, '__all__' significa todos os campos.
        """
        model = Category
        fields = '__all__'
