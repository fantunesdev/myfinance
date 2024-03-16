from rest_framework import serializers

from statement.models import Account


class AccountSerializer(serializers.ModelSerializer):
    """
    Serializador para a classe Account.

    Este serializador converte instâncias da classe Account em dados serializados
    e vice-versa. Ele é usado para integrar objetos Account com o Django REST Framework.

    Attributes:
        model (Account): O modelo associado ao serializador.
        fields (str): Uma string indicando quais campos do modelo devem ser incluídos
                      na serialização. No caso, '__all__' significa todos os campos.
    """

    class Meta:
        """
        Classe aninhada que fornece configurações adicionais para o serializador.

        Attributes:
            model (Account): O modelo associado ao serializador. Neste caso, a classe Account.
            fields (str): Uma string indicando quais campos do modelo devem ser incluídos
                          na serialização. No caso, '__all__' significa todos os campos.
        """

        model = Account
        fields = '__all__'
