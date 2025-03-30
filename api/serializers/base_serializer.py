from rest_framework.serializers import ModelSerializer

class BaseSerializer(ModelSerializer):
    """
    Serializador para a classe Account.
    """

    def __init__(self, *args, model=None, **kwargs):
        if model is not None:
            self.Meta.model = model
        elif not hasattr(self.Meta, 'model'):
            message = 'O argumento "model" deve ser fornecido ao instanciar o BaseSerializer'
            raise ValueError(message)
        super().__init__(*args, **kwargs)

    class Meta:
        """
        Classe aninhada que fornece configurações adicionais para o serializador.
        """

        model = None
        fields = '__all__'
