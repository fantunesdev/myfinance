from django.db.models import QuerySet
from django.forms import modelform_factory
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet


class BaseView(ViewSet):
    """
    Classe padrão para as views da API
    """

    model = None
    service = None
    serializer = None
    statement_view = None

    def __init__(self, *args, **kwargs):
        """
        Inicializador da classe
        """
        super().__init__(*args, **kwargs)
        if self.statement_view:
            self.class_has_user = self.statement_view.class_has_user

    def create(self, request):
        """
        Cria uma nova instância do modelo.

        :param request: Requisição HTTP com os dados para criar a nova instância.
        :return: Response com os dados da nova instância criada.
        """
        user = self._set_user(request)
        serializer = self._get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Converte o dicionário de dados em um formulário do modelo para reaproveitar a BaseService de Statement
        form_class = modelform_factory(self.model, fields='__all__')
        form = form_class(request.data)
        if not form.is_valid():
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)
        instance = self.service.create(form, user)
        serialized_instance = self._get_serializer(instance)
        return Response(serialized_instance.data, status=status.HTTP_201_CREATED)

    def list(self, request):
        """
        Obtém todas as instâncias do modelo

        :param request: Requisição HTTP.
        :return: Response com a lista de instâncias.
        """
        user = self._set_user(request)
        instances = self.service.get_all(user)
        serializer = self._get_serializer(instances, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request, pk=None):
        """
        Obtém uma instância pelo ID.

        :param request: Requisição HTTP.
        :param pk: ID da instância a ser obtida.
        :return: Response com os dados da instância.
        """
        user = self._set_user(request)
        try:
            instance = self.service.get_by_id(pk, user)
            serializer = self._get_serializer(instance)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_404_NOT_FOUND)

    def _get_serializer(self, *args, **kwargs):
        """
        Sobrescreve o método get_serializer para passar o model dinamicamente.

        :param args: Argumentos adicionais (listas).
        :param kwargs: Argumentos adicionais (dicionários).
        :return: Serializer instanciado.
        """
        kwargs['model'] = self.model
        return self.serializer(*args, **kwargs)

    def _serialize_and_return(self, instances):
        has_many = isinstance(instances, QuerySet)
        serializer = self.serializer(instances, many=has_many)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def _set_user(self, request):
        """
        Retorna o usuário da requisição, se necessário.

        :param request: Requisição HTTP.
        :return: Usuário da requisição ou None.
        """
        if self.class_has_user:
            return request.user
        return None
