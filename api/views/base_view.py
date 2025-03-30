from django.db.models import QuerySet
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status

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

    def list(self, request):
        """
        Obtém todas as instâncias do modelo
        """
        user = self._set_user(request)
        instances = self.service.get_all(user)
        serializer = self._get_serializer(instances, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request, pk=None):
        """
        Obtém uma instância pelo ID.
        """
        user = self._set_user(request)
        try:
            instance = self.service.get_by_id(pk, user)
            serializer = self._get_serializer(instance)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
    
    def _get_serializer(self, *args, **kwargs):
        """
        Sobrescreve o método get_serializer para passar o model dinamicamente.
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
        """
        if self.class_has_user:
            return request.user
        return None
