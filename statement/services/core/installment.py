import copy
import datetime
from django.forms.models import model_to_dict

from statement.forms.core.transaction import TransactionForm
from statement.models import Installment
from statement.services.base_service import BaseService
from statement.services.core.card import CardService
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
        :transaction (Transaction): Transação associada à parcela (obrigatório).
        """
        if not transaction:
            raise ValueError("A instância de 'Transaction' é obrigatória para criar um Installment.")

        installment = Installment.objects.create(
            posted_date=transaction.posted_date,
            description=transaction.description,
            user=user,
        )
        cls._set_installments_plan(installment, transaction)
        return installment

    @classmethod
    def _set_installments_plan(cls, installment, transaction):
        """
        Atualiza a primeira parcela e adiciona as demais parcelas
        """
        transaction = cls._set_first_installment(installment, transaction)
        cls._add_installments(transaction)

    @classmethod
    def _set_first_installment(cls, installment, transaction):
        """
        Atribui os valores da primeira parcela e a atualiza
        """
        transaction.installment = installment
        transaction.paid = 1
        if transaction.card:
            transaction.payment_date = CardService.set_processing_date(transaction.card, transaction.posted_date)
        transaction.value = cls._set_transaction_value(transaction)
        cls._update_first_transaction(transaction)
        return transaction

    @classmethod
    def _add_installments(cls, transaction):
        """
        Cadastra as parcelas do parcelamento

        :transaction (models.Transaction): Uma instância do model Transaction.
        """
        start = transaction.paid + 1
        stop = transaction.installments_number + 1

        next_transaction = copy.copy(transaction)

        for i in range(start, stop):
            next_transaction.paid = i
            next_transaction.payment_date = DateTimeUtils.add_months(next_transaction.payment_date, 1)

            # Cria um dicionário com os dados da transação atual (sem o id)
            data = model_to_dict(next_transaction)
            data.pop('id', None)

            # Formata datas e valores para o formulário
            for key, value in list(data.items()):
                if isinstance(value, datetime.date):
                    data[key] = value.strftime('%Y-%m-%d')
                elif isinstance(value, bool):
                    data[key] = 'on' if value else ''
                elif value is None:
                    data[key] = ''

            # Cria um formulário com dados (sem instance) para que o save crie uma nova linha
            transaction_form = TransactionForm(next_transaction.user, data)
            TransactionService.create(transaction_form, next_transaction.user)

    @classmethod
    def _remove_installments(cls, form, transactions):
        """
        Remove parcelas do parcelamento

        :transactions (list): Uma lista do modelo Transaction
        :total (int): Numero total de parcelas depois da remoção
        """
        for transaction in transactions:
            TransactionService.delete(transaction)

    @staticmethod
    def _set_transaction_value(transaction):
        """
        Obtém o valor da primeira parcela
        """
        return transaction.value / transaction.installments_number

    @classmethod
    def _update_first_transaction(cls, transaction):
        """
        Atualiza a primeira parcela.

        :transaction (models.Transaction): Uma instância do model Transaction.
        :value (float): O valor a ser atualizado.
        """
        data = {
            'value': transaction.value,
            'paid': transaction.paid,
            'payment_date': transaction.payment_date,
            'installment': transaction.installment,
        }
        if transaction.card:
            data['posted_date'] = transaction.posted_date
        cls.patch(transaction, data)

    @staticmethod
    def _set_transaction_form(form, transaction):
        """
        Atualiza os valores da transação com os dados do formulário.
        """
        # Criar uma cópia do objeto transaction
        new_transaction = copy.copy(transaction)

        if form.is_valid():
            for field, value in form.cleaned_data.items():
                if hasattr(new_transaction, field):
                    if value is None:
                        original_value = getattr(transaction, field, None)
                        setattr(new_transaction, field, original_value)
                    else:
                        setattr(new_transaction, field, value)

            # Cria uma cópia dos dados do formulário
            form_data = form.data.copy() if hasattr(form.data, 'copy') else dict(form.data)

            # Dinamicamente adiciona todos os campos obrigatórios que não estão no formulário
            for field_name, field in TransactionForm().fields.items():
                # Verifica se o campo é obrigatório e não está nos dados do formulário
                if field.required and (field_name not in form_data or not form_data[field_name]):
                    # Obtém o valor do campo da transação original
                    original_value = getattr(transaction, field_name, None)

                    # Formata o valor dependendo do tipo de campo
                    if original_value is not None:
                        if isinstance(original_value, datetime.date):
                            form_data[field_name] = original_value.strftime('%Y-%m-%d')
                        elif isinstance(original_value, bool):
                            form_data[field_name] = 'on' if original_value else ''
                        elif hasattr(original_value, 'pk'):  # Verifica se é uma instância de modelo
                            form_data[field_name] = str(original_value.pk)
                        else:
                            form_data[field_name] = str(original_value)

            # Preserva o relacionamento com installment
            if hasattr(transaction, 'installment') and transaction.installment:
                new_transaction.installment = transaction.installment
                # Adiciona o ID do installment nos dados do formulário se for um campo no formulário
                if 'installment' in TransactionForm().fields:
                    form_data['installment'] = str(transaction.installment.pk)

            return TransactionForm(data=form_data, files=form.files, instance=new_transaction)
        return form

    @classmethod
    def update_installment_plan(cls, request, form, transactions):
        """
        Gerencia o número de parcelas adicionando ou removendo caso necessário
        """
        transactions_number = transactions.first().installments_number
        form_number = form.cleaned_data['installments_number']


        match form_number:
            case n if n > transactions_number:
                last_transaction = cls._update_transactions(request, form, transactions)
                cls._add_installments(last_transaction)
            case n if n < transactions_number:
                total = transactions_number - form_number
                remove = transactions[:total]
                update = transactions[total:]
                cls._remove_installments(form, remove)
                cls._update_transactions(request, form, update)
            case transactions_number:
                print('apenas atualiza')
                cls._update_transactions(request, form, transactions)

    @classmethod
    def _update_transactions(cls, request, form, transactions):
        """
        Atualiza as parcelas de um parcelamento
        """
        for index, transaction in enumerate(transactions):
            posted_date = form.cleaned_data.get('posted_date')
            if transaction.card:
                payment_date = CardService.set_processing_date(transaction.card, posted_date)
                transaction.payment_date = DateTimeUtils.add_months(payment_date, index)
            else:
                transaction.payment_date = DateTimeUtils.add_months(posted_date, index)
            transaction.paid = index + 1
            transaction_form = cls._set_transaction_form(form, transaction)
            last_transaction = TransactionService.update(transaction_form, transaction)
        return last_transaction

    @classmethod
    def advance_transactions(cls, form, installments):
        """
        Avança uma quantidade de parcelas a partir de uma data
        """
        advanced = 0
        not_advanced = 0
        quantity = form.cleaned_data['quantity']
        initial_date = form.cleaned_data['initial_date']
        next_expiration = CardService.set_processing_date(installments.first().card, initial_date)
        for transaction in installments:
            if transaction.payment_date > initial_date:
                if advanced < quantity:
                    transaction.payment_date = next_expiration
                    form_transaction = TransactionForm(instance=transaction)
                    TransactionService.update(form_transaction, transaction)
                    advanced += 1
                else:
                    not_advanced += 1
                    transaction.payment_date = DateTimeUtils.add_months(next_expiration, not_advanced)
                    form_transaction = TransactionForm(instance=transaction)
                    TransactionService.update(form_transaction, transaction)
