from rest_framework import serializers

from statement.models import Subcategory


class SubcategorySerializer(serializers.ModelSerializer):
    """
    Serializador para a classe Subcategory.

    Este serializador converte instâncias da classe Subcategory em dados serializados
    e vice-versa. Ele é usado para integrar objetos Subcategory com o Django REST Framework.

    Attributes:
        model (Subcategory): O modelo associado ao serializador.
        fields (str): Uma string indicando quais campos do modelo devem ser incluídos
                      na serialização. No caso, '__all__' significa todos os campos.

    """

    class Meta:
        """
        Classe aninhada que fornece configurações adicionais para o serializador.

        Attributes:
            model (Subcategory): O modelo associado ao serializador. Neste caso, a classe Subcategory.
            fields (str): Uma string indicando quais campos do modelo devem ser incluídos
                          na serialização. No caso, '__all__' significa todos os campos.
        """
        model = Subcategory
        fields = '__all__'
