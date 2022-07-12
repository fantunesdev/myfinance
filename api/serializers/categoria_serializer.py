from rest_framework import serializers

from balanco.models import Categoria


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['tipo', 'cor', 'descricao', 'usuario']

    def __init__(self, *args, **kwargs):
        fields = kwargs.pop('fields', None)

        super().__init__(*args, **kwargs)

        if fields is not None:
            allowed = set(fields)
            existing = set(self.fields)
            for fild_name in existing - allowed:
                self.fields.pop(fild_name)
