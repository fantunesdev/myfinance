import copy
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from statement.entities.transaction import Transaction
from statement.forms.general_forms import (
    ExclusionForm,
    NavigationForm,
    UploadFileForm,
)
from statement.repositories import (
    installment_repository,
    next_month_view_repository,
)
from statement.repositories.templatetags_repository import (
    set_dashboard_templatetags,
    set_menu_templatetags,
    set_templatetags,
    set_transaction_navigation_templatetags,
)
from statement.repositories.transaction_repository import *
from statement.services import (
    fixed_expenses_services,
    transaction_installment_services,
)


@login_required
def create_transaction(request, type):
    """
    Cria uma nova transação com base nos dados fornecidos pelo formulário.

    Esta view trata as solicitações POST recebidas do formulário de criação de transações.
    Valida os dados do formulário, cria uma nova transação com base nesses dados e executa
    verificações de saldo da conta e divisão em parcelas. Se a transação for bem-sucedida,
    redireciona para a página de visualização de transações do mês atual.

    Args:
        request (HttpRequest): O objeto de solicitação HTTP enviado pelo cliente.
        type (str): O tipo de transação ('entrada' ou 'saída').

    Returns:
        HttpResponseRedirect ou HttpResponse: Um redirecionamento para a página de visualização
        de transações do mês atual se a transação for bem-sucedida, caso contrário, uma resposta
        HTTP contendo os erros de validação do formulário.
    """
    if request.method == 'POST':
        transaction_form = TransactionForm(request.POST)
        if transaction_form.is_valid():
            transaction = Transaction(
                release_date=transaction_form.cleaned_data['release_date'],
                payment_date=transaction_form.cleaned_data['payment_date'],
                account=transaction_form.cleaned_data['account'],
                card=transaction_form.cleaned_data['card'],
                category=transaction_form.cleaned_data['category'],
                subcategory=transaction_form.cleaned_data['subcategory'],
                description=transaction_form.cleaned_data['description'],
                value=transaction_form.cleaned_data['value'],
                installments_number=transaction_form.cleaned_data[
                    'installments_number'
                ],
                paid=transaction_form.cleaned_data['paid'],
                fixed=transaction_form.cleaned_data['fixed'],
                annual=transaction_form.cleaned_data['annual'],
                currency=transaction_form.cleaned_data['currency'],
                observation=transaction_form.cleaned_data['observation'],
                remember=transaction_form.cleaned_data['remember'],
                type=type,
                effected=transaction_form.cleaned_data['effected'],
                home_screen=transaction_form.cleaned_data['home_screen'],
                user=request.user,
                installment=None,
            )
            home_screen = (
                transaction.account.home_screen
                if transaction.account
                else transaction.card.home_screen
            )
            transaction.home_screen = home_screen
            validate_account_balance(transaction)
            validate_installment(transaction)
            return redirect('get_current_month_transactions')
        else:
            print(transaction_form.errors)
            return transaction_form.errors
    else:
        transaction_form = validate_form_by_type(type, request.user)
        print(request)
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['transaction_form'] = transaction_form
    templatetags['type'] = type
    return render(request, 'transaction/transaction_form.html', templatetags)


@login_required
def import_transactions(request):
    """
    Renderiza a página de importação de transações.

    Esta view renderiza a página de importação de transações, exibindo um formulário para upload
    de arquivos contendo dados de transações. O formulário é inicializado com as permissões
    do usuário atual.

    Args:
        request (HttpRequest): O objeto de solicitação HTTP enviado pelo cliente.

    Returns:
        HttpResponse: Uma resposta HTTP que renderiza a página de importação de transações com
        o formulário de upload de arquivos.
    """
    upload_file_form = UploadFileForm(request.user)
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['upload_file_form'] = upload_file_form
    return render(
        request, 'transaction/import_transactions.html', templatetags
    )


@login_required
def get_transactions(request):
    """
    Renderiza a página de transações do usuário atual.

    Esta view renderiza a página de transações do usuário atual, recuperando todas as transações
    associadas a esse usuário e exibindo-as na página.

    Args:
        request (HttpRequest): O objeto de solicitação HTTP enviado pelo cliente.

    Returns:
        HttpResponse: Uma resposta HTTP que renderiza a página de transações com as transações
        do usuário atual.
    """
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['transactions'] = transaction_services.get_transactions(
        request.user
    )
    return render(request, 'transaction/get_transactions.html', templatetags)


@login_required
def get_transactions_by_description(request, description):
    """
    Renderiza a página de transações filtradas por descrição.

    Esta view renderiza a página de transações filtradas por uma descrição específica, exibindo
    as transações que correspondem à descrição fornecida.

    Args:
        request (HttpRequest): O objeto de solicitação HTTP enviado pelo cliente.
        description (str): A descrição para filtrar as transações.

    Returns:
        HttpResponse: Uma resposta HTTP que renderiza a página de transações filtradas
        pela descrição.
    """
    year = datetime.today().year
    month = datetime.today().month
    transactions = transaction_services.get_transactions_by_description(
        description, request.user
    )
    revenue, expenses, cards, cash, fixed = calculate_total_revenue_expenses(
        transactions
    )
    templatetags = set_templatetags()
    set_dashboard_templatetags(
        templatetags, revenue, expenses, cards, cash, fixed
    )
    set_transaction_navigation_templatetags(templatetags, year, month)
    set_menu_templatetags(request.user, templatetags)
    templatetags['transactions'] = transactions
    templatetags['navigation_form'] = NavigationForm(
        initial={'year': year, 'month': month}
    )
    return render(request, 'transaction/get_transactions.html', templatetags)


@login_required
def get_transactions_by_year(request, year):
    """
    Renderiza a página de transações de um determinado ano.

    Esta view renderiza a página de transações de um determinado ano, exibindo todas as transações
    associadas a esse ano.

    Args:
        request (HttpRequest): O objeto de solicitação HTTP enviado pelo cliente.
        year (int): O ano para o qual as transações devem ser filtradas.

    Returns:
        HttpResponse: Uma resposta HTTP que renderiza a página de transações do ano especificado.
    """
    transactions = transaction_services.get_transactions_by_year(
        year, request.user
    )
    revenue, expenses, cards, cash, fixed = calculate_total_revenue_expenses(
        transactions
    )
    templatetags = set_templatetags()
    set_dashboard_templatetags(
        templatetags, revenue, expenses, cards, cash, fixed
    )
    set_transaction_navigation_templatetags(templatetags, year)
    set_menu_templatetags(request.user, templatetags)
    templatetags['transactions'] = transactions
    return render(request, 'transaction/get_transactions.html', templatetags)


@login_required
def get_current_month_transactions(request):
    """
    Renderiza a página de transações do mês atual.

    Esta view renderiza a página de transações do mês atual do usuário atual, exibindo todas
    as transações associadas a esse mês.

    Args:
        request (HttpRequest): O objeto de solicitação HTTP enviado pelo cliente.

    Returns:
        HttpResponse: Uma resposta HTTP que renderiza a página de transações do mês atual.
    """
    current_month = next_month_view_repository.get_current_month(request.user)
    transactions = transaction_services.get_transactions_by_year_and_month(
        year=current_month.year, month=current_month.month, user=request.user
    )
    revenue, expenses, cards, cash, fixed = calculate_total_revenue_expenses(
        transactions
    )
    templatetags = set_templatetags()
    set_dashboard_templatetags(
        templatetags, revenue, expenses, cards, cash, fixed
    )
    set_transaction_navigation_templatetags(templatetags, current_month)
    set_menu_templatetags(request.user, templatetags)
    templatetags['transactions'] = transactions
    templatetags['navigation_form'] = NavigationForm(
        initial={'year': current_month.year, 'month': current_month.month}
    )
    return render(request, 'transaction/get_transactions.html', templatetags)


@login_required
def get_transactions_by_year_and_month(request, year, month):
    """
    Renderiza a página de transações de um determinado ano e mês.

    Esta view renderiza a página de transações de um determinado ano e mês, exibindo todas
    as transações associadas a esse ano e mês.

    Args:
        request (HttpRequest): O objeto de solicitação HTTP enviado pelo cliente.
        year (int): O ano para o qual as transações devem ser filtradas.
        month (int): O mês para o qual as transações devem ser filtradas.

    Returns:
        HttpResponse: Uma resposta HTTP que renderiza a página de transações do ano e
        mês especificados.
    """
    transactions = transaction_services.get_transactions_by_year_and_month(
        year, month, request.user
    )
    revenue, expenses, cards, cash, fixed = calculate_total_revenue_expenses(
        transactions
    )
    templatetags = set_templatetags()
    set_dashboard_templatetags(
        templatetags, revenue, expenses, cards, cash, fixed
    )
    set_transaction_navigation_templatetags(templatetags, year, month)
    set_menu_templatetags(request.user, templatetags)
    templatetags['transactions'] = transactions
    templatetags['navigation_form'] = NavigationForm(
        initial={'year': year, 'month': month}
    )
    return render(request, 'transaction/get_transactions.html', templatetags)


@login_required
def get_fixed_transactions_by_year_and_month(request, year, month):
    """
    Renderiza a página de transações fixas de um determinado ano e mês.

    Esta view renderiza a página de transações fixas de um determinado ano e mês, exibindo todas
    as transações fixas associadas a esse ano e mês.

    Args:
        request (HttpRequest): O objeto de solicitação HTTP enviado pelo cliente.
        year (int): O ano para o qual as transações fixas devem ser filtradas.
        month (int): O mês para o qual as transações fixas devem ser filtradas.

    Returns:
        HttpResponse: Uma resposta HTTP que renderiza a página de transações fixas do ano e
        mês especificados.
    """
    transactions = (
        transaction_services.get_fixed_transactions_by_year_and_month(
            year, month, request.user
        )
    )
    fixed_expenses = (
        fixed_expenses_services.get_fixed_expenses_by_year_and_month(
            year, month, request.user
        )
    )
    revenue, expenses, cards, cash, fixed = calculate_total_revenue_expenses(
        transactions
    )
    templatetags = set_templatetags()
    set_dashboard_templatetags(
        templatetags, revenue, expenses, cards, cash, fixed
    )
    set_transaction_navigation_templatetags(templatetags, year, month)
    set_menu_templatetags(request.user, templatetags)
    templatetags['transactions'] = transactions
    templatetags['fixed_expenses'] = fixed_expenses
    return render(request, 'transaction/get_transactions.html', templatetags)


@login_required
def detail_transaction(request, id):
    """
    Renderiza a página de detalhes de uma transação.

    Esta view renderiza a página de detalhes de uma transação específica, exibindo todas as
    informações detalhadas sobre essa transação.

    Args:
        request (HttpRequest): O objeto de solicitação HTTP enviado pelo cliente.
        id (int): O ID da transação para a qual os detalhes devem ser exibidos.

    Returns:
        HttpResponse: Uma resposta HTTP que renderiza a página de detalhes da
        transação especificada.
    """
    transaction = transaction_services.get_transaction_by_id(id, request.user)
    templatetags = set_templatetags()
    if transaction.installment:
        transactions = (
            transaction_installment_services.get_transaction_by_installment(
                transaction.parcelamento
            )
        )
        templatetags['transactions'] = transactions
    templatetags['transaction'] = transaction
    set_menu_templatetags(request.user, templatetags)
    return render(request, 'transaction/detail_transaction.html', templatetags)


@login_required
def update_transaction(request, id):
    """
    Atualiza uma transação existente com base nos dados do formulário.

    Esta view trata as solicitações POST recebidas do formulário de edição de transações. Valida os dados do formulário, atualiza a transação existente com base nesses dados e executa verificações de saldo da conta e divisão em parcelas, se aplicável.

    Args:
        request (HttpRequest): O objeto de solicitação HTTP enviado pelo cliente.
        id (int): O ID da transação a ser atualizada.

    Returns:
        HttpResponseRedirect: Um redirecionamento para a página de transações do mês atual após a atualização bem-sucedida da transação.
    """
    old_transaction = transaction_services.get_transaction_by_id(
        id, request.user
    )
    transaction_form = UpdateTransactionForm(
        request.POST or None, instance=old_transaction
    )
    old_transaction_copy = copy.deepcopy(old_transaction)
    if transaction_form.is_valid():
        new_transaction = Transaction(
            release_date=transaction_form.cleaned_data['release_date'],
            payment_date=transaction_form.cleaned_data['payment_date'],
            account=transaction_form.cleaned_data['account'],
            card=transaction_form.cleaned_data['card'],
            category=transaction_form.cleaned_data['category'],
            subcategory=transaction_form.cleaned_data['subcategory'],
            description=transaction_form.cleaned_data['description'],
            value=transaction_form.cleaned_data['value'],
            installments_number=old_transaction.installments_number,
            paid=old_transaction.paid,
            fixed=transaction_form.cleaned_data['fixed'],
            annual=transaction_form.cleaned_data['annual'],
            currency=transaction_form.cleaned_data['currency'],
            observation=transaction_form.cleaned_data['observation'],
            remember=transaction_form.cleaned_data['remember'],
            type=transaction_form.cleaned_data['type'],
            effected=transaction_form.cleaned_data['effected'],
            home_screen=transaction_form.cleaned_data['home_screen'],
            user=request.user,
            installment=old_transaction.installment,
        )
        home_screen = (
            new_transaction.account.home_screen
            if new_transaction.account
            else new_transaction.card.home_screen
        )
        new_transaction.home_screen = home_screen
        validate_new_account_balance(
            old_transaction, new_transaction, old_transaction_copy
        )
        if transaction_form.cleaned_data['installment_option'] == 'parcelar':
            installment_repository.validate_installment(
                old_transaction_copy, new_transaction
            )
            return redirect('get_current_month_transactions')
        else:
            transaction_services.update_transaction(
                old_transaction, new_transaction
            )
        return redirect('get_current_month_transactions')
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['transaction_form'] = transaction_form
    templatetags['old_transaction'] = old_transaction
    return render(request, 'transaction/transaction_form.html', templatetags)


@login_required
def delete_transaction(request, id):
    """
    Exclui uma transação existente.

    Esta view trata as solicitações POST recebidas do formulário de exclusão de transações.
    Exclui a transação existente e executa verificações de saldo da conta, se aplicável.

    Args:
        request (HttpRequest): O objeto de solicitação HTTP enviado pelo cliente.
        id (int): O ID da transação a ser excluída.

    Returns:
        HttpResponseRedirect: Um redirecionamento para a página de transações do mês atual
        após a exclusão bem-sucedida da transação.
    """
    transaction = transaction_services.get_transaction_by_id(id, request.user)
    exclusion_form = ExclusionForm()
    if request.POST.get('confirmation'):
        transaction_services.delete_transaction(transaction)
        validate_account_balance_when_delete_transaction(transaction)
        return redirect('get_current_month_transactions')
    templatetags = set_templatetags()
    templatetags['exclusion_form'] = exclusion_form
    templatetags['transaction'] = transaction
    set_menu_templatetags(request.user, templatetags)
    return render(request, 'transaction/detail_transaction.html', templatetags)
