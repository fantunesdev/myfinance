from rest_framework import serializers

from api.serializers.categoria_serializer import CategoriaSerializer
from balanco.models import Subcategoria


class SubcategoriaSerializer(serializers.ModelSerializer):
    categoria = CategoriaSerializer(fields=('id', 'descricao'))

    class Meta:
        model = Subcategoria
        fields = ['id', 'descricao', 'categoria']

    def __init__(self, *args, **kwargs):
        fields = kwargs.pop('fields', None)

        super().__init__(*args, **kwargs)

        if fields is not None:
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)
