import json

from datetime import date

from dateutil.relativedelta import relativedelta
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.shortcuts import redirect

from clients.transaction_classifier.transaction_classifier import TransactionClassifierClient
from statement.forms.core.transaction import TransactionExpenseForm, TransactionForm, TransactionRevenueForm
from statement.forms.general_forms import NavigationForm, UploadFileForm
from statement.models import Transaction
from statement.services.core.card import CardService
from statement.services.core.fixed_expenses import FixedExpensesService
from statement.services.core.installment import InstallmentService
from statement.services.core.notification import NotificationService
from statement.services.core.transaction import TransactionService
from statement.utils.datetime import DateTimeUtils
from statement.models import CardNumber
import json
from statement.views.base_view import BaseView


class TransactionView(BaseView):
    """
    View responsável pela gestão dos lançamentos
    """

    class_has_user = True
    class_title = 'Lançamento'
    class_form = TransactionForm
    model = Transaction
    service = TransactionService
    redirect_url = 'get_current_month_transactions'

    def __init__(self):
        """
        Atualiza o dicionário template_is_global sem sobrescrever toda a estrutura da classe base.
        """
        super().__init__()
        self.template_is_global.update(
            {
                'create': False,
                'delete': False,
                'get_all': False,
                'detail': False,
                'update': False,
            }
        )
        self._type = None

    def create(self, request, type, id=None):
        self._type = type
        # Custom create to include card_numbers_json in the template context
        self._context = 'create'
        user = self._get_user(request)
        if request.method == 'POST':
            form = self._set_form(request, instance=None)
            if form.is_valid():
                instance = self.service.create(form=form, user=user, id=id)
                self._custom_actions(request=request, form=form, instance=instance)
                return redirect(self.redirect_url)
            else:
                print('Formulário inválido:')
                print(form.errors)
        else:
            form = self._set_form(request, instance=None)

        # Provide card numbers JSON for the form JS
        card_numbers_qs = CardNumber.objects.select_related('card').all()
        card_numbers = list(card_numbers_qs.values('id', 'number', 'name', 'card_id'))

        specific_content = {
            'create': True,
            'card_numbers_json': json.dumps(card_numbers),
        }
        template = self._set_template_by_global_status('create')
        return self._render(request, form, template, specific_content)

    @method_decorator(login_required)
    def get_current_month(self, request):
        """
        View responsável por exibir os lançamentos ano-mês atual.
        """
        year, month = self._get_current_month(request)
        return self.get_by_year_and_month(request, year, month)

    @method_decorator(login_required)
    def get_by_year_and_month(self, request, year, month):
        """
        View responsável por exibir os lançamentos de um ano e mês específicos.
        """
        filters = self._set_monthly_filter_by_date_attr('payment', request.user, year, month, home_screen=True)
        filters.update(self._set_additional_filters())
        instances = self.service.get_by_filter(**filters)
        template = self._set_template_by_global_status('get_all')
        specific_context = self._set_specific_context(instances, year, month)
        return self._render(request, None, template, specific_context)

    @method_decorator(login_required)
    def get_by_year(self, request, year):
        """
        View responsável por exibir os lançamentos de um ano e mês específicos.
        """
        instances = self.service.get_by_filter(payment_date__year=year, user=request.user, home_screen=True)
        template = self._set_template_by_global_status('get_all')
        specific_context = {
            'instances': instances,
            'navigation': {
                'previous': year - 1,
                'current': year,
                'next': year + 1,
            },
        }
        return self._render(request, None, template, specific_context)

    @method_decorator(login_required)
    def get_by_description(self, request, description):

        """
        View de pesquisa, exibe lançamentos por palavras chave
        """
        kwargs = {
            'description__icontains': description,
            'user': request.user,
        }
        instances = self.service.get_by_filter(**kwargs)
        template = self._set_template_by_global_status('get_all')
        specific_context = {'instances': instances}
        return self._render(request, None, template, specific_context)

    @method_decorator(login_required)
    def import_transactions(self, request):
        """
        Página que faz o upload para o carregamento de lançamentos por arquivo
        """
        form = UploadFileForm(request.user)
        
        specific_context = {
            'notifications_json': json.dumps([]),
        }
        
        return self._render(request, form, 'transaction/import.html', specific_context)

    @method_decorator(login_required)
    def import_data(self, request):
        """
        Página que oferece opções de importação: por arquivo ou por notificações
        """
        form = UploadFileForm(request.user)
        
        # Busca as notificações não usadas (vinculadas e não vinculadas)
        notifications = []
        all_notifications = list(NotificationService.get_by_filter(is_used=False))

        # Busca os cartões do usuário para validação
        cards = CardService.get_all(request.user)
        card_ids = {card.id for card in cards}

        # Tenta vincular notificações que ainda não tem cartão associado
        unlinked = [n for n in all_notifications if n.card is None]
        if unlinked:
            CardService.are_notifications_owner(cards, unlinked)
            for n in unlinked:
                # Se o serviço identificou um cartão para a notificação e ela ainda não está vinculada no banco, salva 
                # essa associação.
                if getattr(n, 'card', None):
                    current = NotificationService.get_by_filter(first=True, id=n.id)
                    if current and current.card is None:
                        n.card = n.card
                        n.card_id = n.card.id
                        n.save()

        # Filtra apenas as notificações que pertencem aos cartões do usuário
        user_notifications = [n for n in all_notifications if n.card_id in card_ids]
        
        # Converte as notificações em transações para exibição
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
            notifications.append({
                'id': notification.id,
                'date': transaction_data.get('release_date', '').strftime('%Y-%m-%d') if transaction_data.get('release_date') else '',
                'description': transaction_data.get('description', ''),
                'original_description': notification.message if hasattr(notification, 'message') else '',
                'value': value,
                'category': None,
                'subcategory': None,
                'card_id': notification.card_id,
                'notification_id': notification.id,
            })
        
        specific_context = {
            'file_notifications_json': json.dumps([]),
            'notifications_json': json.dumps(notifications),
            'has_notifications': len(notifications) > 0,
        }
        
        return self._render(request, form, 'transaction/import_base.html', specific_context)

    def _get_current_month(self, request):
        """
        Obtém o mês atual levando em conta a configuração de "next month view" do perfil.
        Se o usuário habilitou e o dia atual for maior ou igual ao configurado, avança um mês.
        """
        today = now()
        from statement.services.next_month_view import NextMonthViewService

        try:
            nm = NextMonthViewService.get(request.user)
        except Exception:
            nm = None

        if nm and getattr(nm, 'active', False):
            try:
                day = int(getattr(nm, 'day', 0))
            except Exception:
                day = 0
            if day > 0 and today.day >= day:
                dt = today + relativedelta(months=1)
                return [dt.year, dt.month]
        return [today.year, today.month]

    def _set_monthly_filter_by_date_attr(self, attr, user, year, month, **extra_filters):
        """
        Seta os filtros por data, seja payment_date ou release_date.
        """
        return {
            f'{attr}_date__year': year,
            f'{attr}_date__month': month,
            'user': user,
            **extra_filters,
        }

    def _set_additional_filters(self, **kwargs):
        """
        Método que permite subclasses adicionarem filtros específicos.

        :kwargs (dict): Os filtros para o select.

        :seealso: Consulte os atributos do modelo em statement/models.py
        :seealso: https://docs.djangoproject.com/en/4.2/ref/models/querysets/#filter
        """
        return {}

    def _set_specific_context(self, instances, year, month, **kwargs):
        # Provide card numbers data to templates (as JSON) so client-side
        # form logic can populate the card_number select dynamically.
        card_numbers_qs = CardNumber.objects.select_related('card').all()
        card_numbers = list(card_numbers_qs.values('id', 'number', 'name', 'card_id'))
        return {
            'instances': instances,
            **self._set_dashboard_templatetags(instances, year, month),
            **self.set_navigation_templatetags(year, month),
            'year_month': DateTimeUtils.date(year, month, 1),
            'card_numbers_json': json.dumps(card_numbers),
            **kwargs,
        }

    def _set_dashboard_templatetags(self, instances, year, month):
        """
        Seta as templatetags de receitas, despesas, cartões, dinheiro e fixas para o dashboard
        """
        revenue = 0
        expenses = 0
        card = 0
        cash = 0
        fixed = 0
        for instance in instances:
            if instance.type == 'saida':   # Saídas
                # Contabiliza apenas os lançamentos das categorias não ignoradas.
                if not instance.category.ignore:
                    # Despesas com cartão
                    if instance.card:
                        card += instance.value
                    # Despesas à vista
                    else:
                        cash += instance.value

                    # Contagem das despesas fixas
                    if instance.fixed:
                        fixed += instance.value

                    # Contagem total de gastos
                    expenses += instance.value
                if instance.category.id == 5:   # Força a contagem para categorias do tipo Aplicação
                    expenses += instance.value
            else:   # Entradas
                revenue += instance.value
        if instances:
            fixed_expenses = FixedExpensesService.get_active_by_date(year, month, instances[0].user)
            fixed += sum(map(lambda x: x.value, fixed_expenses))
        return {
            'dashboard': {
                'card': card,
                'cash': cash,
                'difference': revenue - expenses,
                'expenses': expenses,
                'fixed': fixed,
                'revenue': revenue,
            }
        }

    def _set_form(self, request, instance):
        """
        Permite que subclasses customizem o formulário
        """
        match self._context:
            case 'create':
                if request.method == 'POST':
                    post_data = request.POST.dict()
                    post_data['type'] = self._type
                    return self.class_form(request.user, post_data, request.FILES or None)
                if self._type == 'entrada':
                    return TransactionRevenueForm(request.user)
                return TransactionExpenseForm(request.user)
            case 'update':
                if request.method == 'POST':
                    return self.class_form(request.user, request.POST, request.FILES, instance=instance)
                else:
                    return self.class_form(request.user, instance=instance)
            case _:
                raise ValueError('Sem contexto definido.')

    def _custom_actions(self, request, form, instance):
        """
        Sobrescreve o método da classe mãe para adicionar ações depois que as ações de create, update ou delete
        são executadas.

        :request (django.http.HttpRequest): - Informações sobre o cabeçalho, método e outros dados da requisição.
        :form (ModelForm): O formulário do modelo da instância.
        :instance: A instância criada, atualizada ou removida no banco de dados.
        """
        match self._context:
            case 'create':
                if instance.installments_number > 0:
                    user = self._get_user(request)
                    InstallmentService.create(form=form, user=user, transaction=instance)
            case 'update':
                pass

    def set_navigation_templatetags(self, year, month):
        """
        Seta as templatetags para o menu superior de navegação por mês e ano.

        :year (int): Ano.
        :month (int): Mês.
        """
        year_month = date(year, month, 1)
        next_month = year_month + relativedelta(months=1)
        previous_month = year_month - relativedelta(months=1)
        return {
            'navigation': {
                'previous': previous_month,
                'next': next_month,
                'month': month,
                'year': year,
                'form': NavigationForm(initial={'year': year, 'month': month}),
            }
        }
