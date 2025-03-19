from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.utils.decorators import method_decorator

from statement.forms.core.installment import InstallmentForm, AdvanceInstallmentForm
from statement.models import Installment
from statement.services.core.installment import InstallmentService
from statement.services.core.transaction import TransactionService
from statement.views.base_view import BaseView


class InstallmentView(BaseView):
    """
    View responsável pela gestão dos parcelamentos
    """

    class_has_user = True
    class_title = 'Parcelamento'
    class_form = InstallmentForm
    model = Installment
    service = InstallmentService
    redirect_url = 'get_current_month_transactions'


    def __init__(self):
        """
        Atualiza o dicionário template_is_global sem sobrescrever toda a estrutura da classe base.
        """
        super().__init__()
        self.template_is_global.update(
            {
                'delete': False,
                'detail': False,
                'update': False,
            }
        )
        self._first_transaction = None

    def update(self, request, id):
        self._first_transaction = self._get_transaction(request, id)
        return super().update(request, id)

    @method_decorator(login_required)
    def advance_transactions(self, request, id):
        user = self._get_user(request)
        installment = self.service.get_by_id(id, user)
        transactions = TransactionService.get_by_filter(installment=installment)
        print(transactions)
        if request.method == 'POST':
            form = AdvanceInstallmentForm(request.POST)
            if form.is_valid():
                InstallmentService.advance_transactions(form, transactions)
                return redirect(self.redirect_url)
            else:
                print(form.errors)
        else:
            form = AdvanceInstallmentForm()
        specific_content = {
            'transactions': transactions
        }
        return self._render(request, form, 'installment/advance.html', specific_content)


    def _get_transactions(self, request, id):
        """
        Obtém as parcelas de um parcelamento.

        :request (django.http.HttpRequest): - Informações sobre o cabeçalho, método e outros dados da requisição.
        :id (int): A chave primária do parcelamento
        """
        kwargs = {
            'installment': id,
            'user': request.user,
        }
        transactions = TransactionService.get_by_filter(**kwargs)
        return transactions

    def _get_transaction(self, request, id):
        """
        Obtém as parcelas de um parcelamento.

        :request (django.http.HttpRequest): - Informações sobre o cabeçalho, método e outros dados da requisição.
        :id (int): A chave primária do parcelamento
        """
        kwargs = {
            'installment': id,
            'user': request.user,
        }
        transactions = TransactionService.get_by_filter(first=True, **kwargs)
        return transactions

    def _add_context_on_templatetags(self, request, instance):
        return {
            'transactions': TransactionService.get_by_filter(installment=instance)
        }

    def _set_form(self, request, instance):
        """
        Sobrescreve a função da classe pai para retornar um formulário customizado
        """
        return InstallmentForm(request.POST or None, instance=self._first_transaction)

    def _custom_actions(self, request, form, instance):
        """
        Sobrescreve o método da classe mãe para adicionar ações depois que as ações de create, update ou delete 
        são executadas.

        :request (django.http.HttpRequest): - Informações sobre o cabeçalho, método e outros dados da requisição.
        :form (ModelForm): O formulário do modelo da instância.
        :instance: A instância criada, atualizada ou removida no banco de dados.
        """
        match self._context:
            case 'update':
                transactions = self._get_transactions(request, instance.id)
                InstallmentService.update_installment_plan(request, form, transactions)
