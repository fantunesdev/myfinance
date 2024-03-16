from rest_framework import serializers

from statement.models import Card


class CardSerializer(serializers.ModelSerializer):
    """
    Serializador para a classe Card.

    Este serializador converte instâncias da classe Card em dados serializados
    e vice-versa. Ele é usado para integrar objetos Card com o Django REST Framework.

    Attributes:
        model (Card): O modelo associado ao serializador.
        fields (str): Uma string indicando quais campos do modelo devem ser incluídos
                      na serialização. No caso, '__all__' significa todos os campos.

    """

    class Meta:
        """
        Classe aninhada que fornece configurações adicionais para o serializador.

        Attributes:
            model (Card): O modelo associado ao serializador. Neste caso, a classe Card.
            fields (str): Uma string indicando quais campos do modelo devem ser incluídos
                          na serialização. No caso, '__all__' significa todos os campos.
        """

        model = Card
        fields = '__all__'
