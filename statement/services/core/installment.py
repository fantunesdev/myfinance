from statement.forms.core.transaction import TransactionForm
from statement.models import Installment
from statement.services.base_service import BaseService
from statement.services.core.transaction import TransactionService
from statement.utils.datetime import DateTimeUtils


class InstallmentService(BaseService):
    """Serviço para gerenciar operações relacionadas ao modelo Installment."""

    model = Installment
    user_field = 'user'

    @classmethod
    def create(cls, form, user=None, id=None, transaction=None):
        """
        Sobrescreve o método pai adicionando o nome e a data de lançamento do parcelamento a partir da primeira parcela.

        :form (ModelForm): Formulário do model da instância.
        :user (models.User): Usuário da requisição
        :id (int): Usado para classes filhas que precisam receber o id da classe mãe.
        """
        return Installment.objects.create(
            release_date = transaction.release_date,
            description = transaction.description,
            user = user,
        )

    @classmethod
    def add_installments(cls, transaction):
        """
        Cadastra as parcelas do parcelamento

        :transaction (models.Transaction): Uma instância do model Transaction.
        """
        installments_number = transaction.installments_number
        value = cls._set_installment_value(transaction)
        if transaction.card:
            transaction.release_date = TransactionService.set_card_release_date(transaction)
        cls._update_first_transaction_installment(transaction, value)
        for i in range(1, installments_number):
            transaction.paid += i
            transaction.value = value
            transaction.payment_date = DateTimeUtils.add_months(transaction.payment_date, i)
            transaction_form = cls.instance_to_form(transaction, TransactionForm)
            TransactionService.create(transaction_form, transaction.user)

    @staticmethod
    def _set_installment_value(transaction):
        """
        Obtém o valor da primeira parcela
        """
        return transaction.value / transaction.installments_number

    @classmethod
    def _update_first_transaction_installment(cls, transaction, new_value):
        """
        Atualiza a primeira parcela.

        :transaction (models.Transaction): Uma instância do model Transaction.
        :value (float): O valor a ser atualizado.
        """
        if transaction.paid > 0:   # Vai transformar uma parcela num lançamento comum
            data = {
                'value': new_value,
                'paid': 0,
                'installment': None,
            }
            cls.patch(transaction, data)
        else:   # transforma um lançamento comum em uma parcela
            data = {
                'value': new_value,
                'paid': 1,
                'installment': transaction.installment
            }
            if transaction.card:
                data['release_date'] = transaction.release_date
            cls.patch(transaction, data)
