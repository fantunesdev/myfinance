from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.response import Response

from api.serializers.base_serializer import BaseSerializer
from api.views.base_view import BaseView
from statement.models import Notification
from statement.services.core.notification import NotificationService
from statement.views.core.notification import NotificationView as StatementView


class NotificationView(BaseView):
    """
    Classe que gerencia a view das notificações na API.
    """

    model = Notification
    service = NotificationService
    serializer = BaseSerializer
    statement_view = StatementView

    def partial_update(self, request, pk=None):
        """
        Atualiza parcialmente uma notificação via PATCH.

        :param request: Requisição HTTP com os dados para atualizar.
        :param pk: ID da notificação a ser atualizada.
        :return: Response com os dados atualizados.
        """
        try:
            instance = self.service.get_by_id(pk)
            # Usa o método patch da BaseService para atualizar apenas os campos fornecidos
            updated_instance = self.service.patch(instance, dict(request.data))
            serializer = self._get_serializer(updated_instance)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist:
            return Response({'detail': 'Notificação não encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
