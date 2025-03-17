from datetime import date

from dateutil.relativedelta import relativedelta
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.utils.timezone import now

from statement.forms.core.transaction import TransactionExpenseForm, TransactionForm, TransactionRevenueForm
from statement.forms.general_forms import NavigationForm
from statement.models import Transaction
from statement.services.core.installment import InstallmentService
from statement.services.core.fixed_expenses import FixedExpensesService
from statement.services.core.transaction import TransactionService
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
        return super().create(request, id)

    @method_decorator(login_required)
    def get_current_month(self, request):
        """
        View responsável por exibir os lançamentos ano-mês atual.
        """
        year, month = self._get_current_month()
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
        specific_context = self._set_specific_cotext(instances, year, month)
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

    def _get_current_month(self):
        """
        Obtém o mês atual
        """
        today = now()
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

    def _set_specific_cotext(self, instances, year, month):
        return {
            'instances': instances,
            **self._set_dashboard_templatetags(instances, year, month),
            **self.set_navigation_templatetags(year, month),
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
                    return TransactionForm(request.POST, request.FILES or None)
                if self._type == 'entrada':
                    return TransactionRevenueForm(request)
                return TransactionExpenseForm(request)
            case 'update':
                return self.class_form(request.POST or None, request.FILES or None, instance=instance)
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
                if instance.installments_number > 0:
                    user = self._get_user(request)
                    InstallmentService.create(form=form, user=user, transaction=instance)


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
