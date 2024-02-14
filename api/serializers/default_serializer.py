from rest_framework import serializers


class DefaultsSerializer(serializers.Serializer):
    """
    Serializador para representar padrões.

    Este serializador é usado para representar dados padrão. É utilizado
    para transmitir informações de configuração ou padrões.

    Attributes:
        version (str): A versão do programa.
        year (int): O ano atual.

    """

    version = serializers.CharField()
    year = serializers.IntegerField()
