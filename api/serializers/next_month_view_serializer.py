from rest_framework import serializers

from statement.models import NextMonthView


class NextMonthViewSerializer(serializers.ModelSerializer):
    """
    Serializador para a classe NextMonthView.

    Este serializador converte instâncias da classe NextMonthView em dados serializados
    e vice-versa. Ele é usado para integrar objetos NextMonthView com o Django REST Framework.

    Attributes:
        model (NextMonthView): O modelo associado ao serializador.
        fields (str): Uma string indicando quais campos do modelo devem ser incluídos
                      na serialização. No caso, '__all__' significa todos os campos.

    """

    class Meta:
        """
        Classe aninhada que fornece configurações adicionais para o serializador.

        Attributes:
            model (NextMonthView): O modelo associado ao serializador. Neste caso, a classe NextMonthView.
            fields (str): Uma string indicando quais campos do modelo devem ser incluídos
                          na serialização. No caso, '__all__' significa todos os campos.
        """

        model = NextMonthView
        fields = '__all__'
