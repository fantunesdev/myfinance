from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.utils.timezone import now
import json

from statement.forms.core.card import CardForm, CardNumberFormSet
from statement.models import Card
from statement.services.core.card import CardService
from statement.services.core.notification import NotificationService
from statement.views.base_view import BaseView


class CardView(BaseView):
    """
    View responsável pela gestão dos cartões
    """

    class_has_user = True
    class_title = 'Cartão'
    class_form = CardForm
    model = Card
    service = CardService
    redirect_url = 'get_profile'
    template_is_global = {
        'create': False,
        'delete': True,
        'detail': True,
        'get_all': True,
        'update': False,
    }

    def create(self, request, id=None):
        """
        Cria uma nova instância do cartão com seus números.
        """
        self._context = 'create'
        user = self._get_user(request)

        if request.method == 'POST':
            form = self._set_form(request, instance=None)
            formset = CardNumberFormSet(request.POST, instance=None)

            if form.is_valid() and formset.is_valid():
                instance = form.save(commit=False)
                instance.user = user
                instance.save()

                # Associa o cartão ao formset antes de salvar
                formset.instance = instance
                formset.save()

                self._custom_actions(request=request, form=form, instance=instance)
                return redirect(self.redirect_url)
            else:
                print('Formulário ou formset inválido:')
                if form.errors:
                    print('Erros do formulário:', form.errors)
                if formset.errors:
                    print('Erros do formset:', formset.errors)
        else:
            form = self._set_form(request, instance=None)
            formset = CardNumberFormSet(instance=None)

        specific_content = {
            'create': True,
            'formset': formset,
        }
        template = self._set_template_by_global_status('create')
        return self._render(request, form, template, specific_content)

    def update(self, request, id):
        """
        Atualiza uma instância existente do cartão com seus números.
        """
        self._context = 'update'
        instance = self.service.get_by_id(id)
        original_instance = type(instance).objects.get(pk=instance.pk)

        if request.method == 'POST':
            form = self._set_form(request, instance)
            formset = CardNumberFormSet(request.POST, instance=instance)

            if form.is_valid() and formset.is_valid():
                self._preserve_unrendered_fields_after_validation(form, original_instance)
                self._custom_actions(request=request, form=form, instance=form.instance)
                self.service.update(form, form.instance)
                formset.save()
                return redirect(self.redirect_url)
            else:
                print('Formulário ou formset inválido:')
                if form.errors:
                    print('Erros do formulário:', form.errors)
                if formset.errors:
                    print('Erros do formset:', formset.errors)
        else:
            form = self._set_form(request, instance)
            formset = CardNumberFormSet(instance=instance)

        additional_context = self._add_context_on_templatetags(request, instance)
        specific_content = {
            'old_instance': instance,
            'update': True,
            'formset': formset,
            **additional_context,
        }
        template = self._set_template_by_global_status('update')
        return self._render(request, form, template, specific_content)
    @method_decorator(login_required)
    def import_notifications(self, request):
        """
        Página que exibe e permite importar transações a partir de notificações dos cartões do usuário
        """
        # Pega todos os cartões do usuário
        cards = self.service.get_all(request.user)

        # Se não houver cartões, retorna sem notificações
        if not cards:
            return self._render(request, None, 'card/import_notifications.html', {
                'notifications_json': json.dumps([]),
                'cards': cards,
            })

        # Pega todas as notificações não usadas que têm cartão associado
        notifications = list(NotificationService.get_by_filter(is_used=False, card__isnull=False))
        
        # Filtra apenas as notificações que pertencem aos cartões do usuário
        card_ids = {card.id for card in cards}
        user_notifications = [n for n in notifications if n.card_id in card_ids]

        # Converte as notificações em transações para exibição
        transactions = []
        for notification in user_notifications:
            transaction_data = NotificationService.build_transaction_from_notification(notification, notification.card)
            # Formata para o padrão do JavaScript
            value = transaction_data.get('value', '')
            if isinstance(value, str):
                value = value.replace(',', '.')  # Converte formato BR para padrão
                try:
                    value = float(value)
                except (ValueError, TypeError):
                    value = 0

            # TODO: Quando usar notificações em produção, integrar transactionClassifier para predição de categorias
            # Por enquanto, category e subcategory são deixados como None para o usuário preencher manualmente
            transactions.append({
                'id': notification.id,  # ID temporário da notificação (será usado para identificação)
                'date': transaction_data.get('release_date', '').strftime('%Y-%m-%d') if transaction_data.get('release_date') else '',
                'description': transaction_data.get('description', ''),
                'original_description': notification.message if hasattr(notification, 'message') else '',
                'value': value,
                'category': None,  # Sem IA em desenvolvimento
                'subcategory': None,  # Sem IA em desenvolvimento
                'card_id': notification.card_id,
                'notification_id': notification.id,
            })

        specific_context = {
            'notifications_json': json.dumps(transactions),
            'cards': cards,
        }

        return self._render(request, None, 'card/import_notifications.html', specific_context)