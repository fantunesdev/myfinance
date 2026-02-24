from django.core.exceptions import ObjectDoesNotExist
from django.forms import modelform_factory
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.response import Response

from api.serializers.base_serializer import BaseSerializer
from api.views.base_view import BaseView
from statement.models import Notification
from statement.services.core.notification import NotificationService
from statement.views.core.notification import NotificationView as StatementView
from statement.services.core.card import CardService


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

    def create(self, request):
        """
        Cria uma notificação, permitindo que o cliente envie `created_at` ou `date`.
        Se fornecido, tenta parsear a data e atribuí-la antes de salvar a instância.
        """
        # Reaproveita a lógica de form do BaseView, mas define created_at manualmente
        form_class = modelform_factory(self.model, exclude=['user'])
        form = form_class(request.data)

        if not form.is_valid():
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)

        instance = form.save(commit=False)
        # Vincula o usuário autenticado automaticamente
        instance.user = request.user

        # Tenta identificar o cartão proprietário da notificação antes de salvar.
        try:
            # Busca todos os cartões do usuário e verifica posse da notificação
            cards = CardService.get_all(request.user)
            CardService.are_notifications_owner(cards, [instance])
            # Se um cartão foi identificado, atribui à instância
            if getattr(instance, 'card_id', None):
                try:
                    instance.card = CardService.get_by_id(instance.card_id, user=request.user)
                except Exception:
                    # Não falhar o fluxo se não conseguir resolver o cartão
                    instance.card = None
        except Exception:
            # Não interrompe a criação se a lógica de binding falhar
            pass

        # Procura por campos de data no payload (client pode enviar 'created_at' ou 'date')
        raw_date = request.data.get('created_at') or request.data.get('date')
        if raw_date:
            # Tenta parse seguro com parse_datetime, caindo para formato comum se necessário
            dt = parse_datetime(raw_date)
            if dt is None:
                try:
                    # formato esperado: 'YYYY-MM-DD HH:MM:SS'
                    from datetime import datetime

                    dt = datetime.strptime(raw_date, '%Y-%m-%d %H:%M:%S')
                except Exception:
                    dt = None

            if dt is not None:
                # Garantir timezone-aware
                if timezone.is_naive(dt):
                    dt = timezone.make_aware(dt, timezone.get_current_timezone())
                    instance.created_at = dt

        # Salva a instância (Notification.class_has_user é False segundo StatementView)
        instance.save()

        # Se o cliente forneceu uma data, atualiza diretamente no banco para
        # contornar o comportamento de `auto_now_add` que pode sobrescrever o valor.
        if raw_date and dt is not None:
            Notification.objects.filter(pk=instance.pk).update(created_at=dt)
            instance.refresh_from_db()

        serializer = self._get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
