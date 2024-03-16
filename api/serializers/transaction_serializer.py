from rest_framework import serializers

from statement.models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    """
    Serializador para a classe Transaction.

    Este serializador converte instâncias da classe Transaction em dados serializados
    e vice-versa. Ele é usado para integrar objetos Transaction com o Django REST Framework.

    Attributes:
        model (Transaction): O modelo associado ao serializador.
        fields (str): Uma string indicando quais campos do modelo devem ser incluídos
                      na serialização. No caso, '__all__' significa todos os campos.

    """

    class Meta:
        """
        Classe aninhada que fornece configurações adicionais para o serializador.

        Attributes:
            model (Transaction): O modelo associado ao serializador. Neste caso, a classe Transaction.
            fields (str): Uma string indicando quais campos do modelo devem ser incluídos
                          na serialização. No caso, '__all__' significa todos os campos.
        """

        model = Transaction
        fields = '__all__'
