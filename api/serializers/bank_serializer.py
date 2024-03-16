from rest_framework import serializers

from statement.models import Bank


class BankSerializer(serializers.ModelSerializer):
    """
    Serializador para a classe Bank.

    Este serializador converte instâncias da classe Bank em dados serializados
    e vice-versa. Ele é usado para integrar objetos Bank com o Django REST Framework.

    Attributes:
        model (Bank): O modelo associado ao serializador.
        fields (str): Uma string indicando quais campos do modelo devem ser incluídos
                      na serialização. No caso, '__all__' significa todos os campos.

    """

    class Meta:
        """
        Classe aninhada que fornece configurações adicionais para o serializador.

        Attributes:
            model (Bank): O modelo associado ao serializador. Neste caso, a classe Bank.
            fields (str): Uma string indicando quais campos do modelo devem ser incluídos
                          na serialização. No caso, '__all__' significa todos os campos.
        """

        model = Bank
        fields = '__all__'
