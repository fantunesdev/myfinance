from  rest_framework import serializers

from balanco.models import Cartao


class CartaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cartao
        fields = ['bandeira', 'icone', 'descricao', 'limite', 'conta', 'vencimento', 'fechamento', 'tela_inicial']
