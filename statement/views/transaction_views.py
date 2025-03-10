import copy
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from statement.entities.transaction import Transaction
from statement.forms.general_forms import ExclusionForm, NavigationForm, UploadFileForm
from statement.repositories import installment_repository, next_month_view_repository
from statement.repositories.templatetags_repository import (
    set_dashboard_templatetags,
    set_menu_templatetags,
    set_templatetags,
    set_transaction_navigation_templatetags,
)
from statement.repositories.transaction_repository import *
from statement.services import fixed_expenses_services, transaction_installment_services


@login_required
def create_transaction(request, type):
    """
    Cria um novo lançamento com base nos dados fornecidos pelo formulário.

    Esta view trata as solicitações POST recebidas do formulário de criação de lançamentos.
    Valida os dados do formulário, cria um novo lançamento com base nesses dados e executa
    verificações de saldo da conta e divisão em parcelas. Se o lançamento for bem-sucedido,
    redireciona para a página de visualização de lançamentos do mês atual.

    Args:
        request (HttpRequest): O objeto de solicitação HTTP enviado pelo cliente.
        type (str): O tipo de lançamento ('entrada' ou 'saída').

    Returns:
        HttpResponseRedirect ou HttpResponse: Um redirecionamento para a página de visualização
        de lançamentos do mês atual se o lançamento for bem-sucedido, caso contrário, uma resposta
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
                installments_number=transaction_form.cleaned_data['installments_number'],
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
                transaction.account.home_screen if transaction.account else transaction.card.home_screen
            )
            transaction.home_screen = home_screen
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
    Renderiza a página de importação de lançamentos.

    Esta view renderiza a página de importação de lançamentos, exibindo um formulário para upload
    de arquivos contendo dados de lançamentos. O formulário é inicializado com as permissões
    do usuário atual.

    Args:
        request (HttpRequest): O objeto de solicitação HTTP enviado pelo cliente.

    Returns:
        HttpResponse: Uma resposta HTTP que renderiza a página de importação de lançamentos com
        o formulário de upload de arquivos.
    """
    upload_file_form = UploadFileForm(request.user)
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['upload_file_form'] = upload_file_form
    return render(request, 'transaction/import_transactions.html', templatetags)


@login_required
def get_transactions(request):
    """
    Renderiza a página de lançamentos do usuário atual.

    Esta view renderiza a página de lançamentos do usuário atual, recuperando todos os lançamento
    associadas a esse usuário e exibindo-as na página.

    Args:
        request (HttpRequest): O objeto de solicitação HTTP enviado pelo cliente.

    Returns:
        HttpResponse: Uma resposta HTTP que renderiza a página de lançamentos com os lançamento
        do usuário atual.
    """
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['transactions'] = transaction_services.get_transactions(request.user)
    return render(request, 'transaction/get_transactions.html', templatetags)


@login_required
def get_transactions_by_description(request, description):
    """
    Renderiza a página de lançamentos filtradas por descrição.

    Esta view renderiza a página de lançamentos filtradas por uma descrição específica, exibindo
    os lançamentos que correspondem à descrição fornecida.

    Args:
        request (HttpRequest): O objeto de solicitação HTTP enviado pelo cliente.
        description (str): A descrição para filtrar os lançamentos.

    Returns:
        HttpResponse: Uma resposta HTTP que renderiza a página de lançamentos filtradas
        pela descrição.
    """
    year = datetime.today().year
    month = datetime.today().month
    transactions = transaction_services.get_transactions_by_description(description, request.user)
    revenue, expenses, cards, cash, fixed = calculate_total_revenue_expenses(transactions, year, month)
    templatetags = set_templatetags()
    set_dashboard_templatetags(templatetags, revenue, expenses, cards, cash, fixed)
    set_transaction_navigation_templatetags(templatetags, year, month)
    set_menu_templatetags(request.user, templatetags)
    templatetags['transactions'] = transactions
    templatetags['navigation_form'] = NavigationForm(initial={'year': year, 'month': month})
    return render(request, 'transaction/get_transactions.html', templatetags)


@login_required
def get_transactions_by_year(request, year):
    """
    Renderiza a página de lançamentos de um determinado ano.

    Esta view renderiza a página de lançamentos de um determinado ano, exibindo todos os lançamento
    associadas a esse ano.

    Args:
        request (HttpRequest): O objeto de solicitação HTTP enviado pelo cliente.
        year (int): O ano para o qual os lançamentos devem ser filtradas.

    Returns:
        HttpResponse: Uma resposta HTTP que renderiza a página de lançamentos do ano especificado.
    """
    transactions = transaction_services.get_transactions_by_year(year, request.user)
    revenue, expenses, cards, cash, fixed = calculate_total_revenue_expenses(transactions, year, 1)
    templatetags = set_templatetags()
    set_dashboard_templatetags(templatetags, revenue, expenses, cards, cash, fixed)
    set_transaction_navigation_templatetags(templatetags, year)
    set_menu_templatetags(request.user, templatetags)
    templatetags['transactions'] = transactions
    return render(request, 'transaction/get_transactions.html', templatetags)


@login_required
def get_current_month_transactions(request):
    """
    Renderiza a página de lançamentos do mês atual.

    Esta view renderiza a página de lançamentos do mês atual do usuário atual, exibindo todas
    os lançamentos associadas a esse mês.

    Args:
        request (HttpRequest): O objeto de solicitação HTTP enviado pelo cliente.

    Returns:
        HttpResponse: Uma resposta HTTP que renderiza a página de lançamentos do mês atual.
    """
    current_month = next_month_view_repository.get_current_month(request.user)
    year = current_month.year
    month = current_month.month
    transactions = transaction_services.get_transactions_by_year_and_month(
        year=year, month=month, user=request.user
    )
    revenue, expenses, cards, cash, fixed = calculate_total_revenue_expenses(transactions, year, month)
    templatetags = set_templatetags()
    set_dashboard_templatetags(templatetags, revenue, expenses, cards, cash, fixed)
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
    Renderiza a página de lançamentos de um determinado ano e mês.

    Esta view renderiza a página de lançamentos de um determinado ano e mês, exibindo todas
    os lançamentos associadas a esse ano e mês.

    Args:
        request (HttpRequest): O objeto de solicitação HTTP enviado pelo cliente.
        year (int): O ano para o qual os lançamentos devem ser filtradas.
        month (int): O mês para o qual os lançamentos devem ser filtradas.

    Returns:
        HttpResponse: Uma resposta HTTP que renderiza a página de lançamentos do ano e
        mês especificados.
    """
    transactions = transaction_services.get_transactions_by_year_and_month(year, month, request.user)
    revenue, expenses, cards, cash, fixed = calculate_total_revenue_expenses(transactions, year, month)
    templatetags = set_templatetags()
    set_dashboard_templatetags(templatetags, revenue, expenses, cards, cash, fixed)
    set_transaction_navigation_templatetags(templatetags, year, month)
    set_menu_templatetags(request.user, templatetags)
    templatetags['transactions'] = transactions
    templatetags['navigation_form'] = NavigationForm(initial={'year': year, 'month': month})
    return render(request, 'transaction/get_transactions.html', templatetags)


@login_required
def get_fixed_transactions_by_year_and_month(request, year, month):
    """
    Renderiza a página de lançamentos fixas de um determinado ano e mês.

    Esta view renderiza a página de lançamentos fixas de um determinado ano e mês, exibindo todas
    os lançamentos fixas associadas a esse ano e mês.

    Args:
        request (HttpRequest): O objeto de solicitação HTTP enviado pelo cliente.
        year (int): O ano para o qual os lançamentos fixas devem ser filtradas.
        month (int): O mês para o qual os lançamentos fixas devem ser filtradas.

    Returns:
        HttpResponse: Uma resposta HTTP que renderiza a página de lançamentos fixas do ano e
        mês especificados.
    """
    transactions = transaction_services.get_fixed_transactions_by_year_and_month(year, month, request.user)
    fixed_expenses = fixed_expenses_services.get_fixed_expenses_by_year_and_month(year, month, request.user)
    revenue, expenses, cards, cash, fixed = calculate_total_revenue_expenses(transactions, year, month)
    templatetags = set_templatetags()
    set_dashboard_templatetags(templatetags, revenue, expenses, cards, cash, fixed)
    set_transaction_navigation_templatetags(templatetags, year, month)
    set_menu_templatetags(request.user, templatetags)
    templatetags['transactions'] = transactions
    templatetags['fixed_expenses'] = fixed_expenses
    return render(request, 'transaction/get_transactions.html', templatetags)


@login_required
def detail_transaction(request, id):
    """
    Renderiza a página de detalhes de um lançamento.

    Esta view renderiza a página de detalhes de um lançamento específica, exibindo todas as
    informações detalhadas sobre esso lançamento.

    Args:
        request (HttpRequest): O objeto de solicitação HTTP enviado pelo cliente.
        id (int): O ID do lançamento para a qual os detalhes devem ser exibidos.

    Returns:
        HttpResponse: Uma resposta HTTP que renderiza a página de detalhes do
        lançamento especificado.
    """
    transaction = transaction_services.get_transaction_by_id(id, request.user)
    templatetags = set_templatetags()
    if transaction.installment:
        transactions = transaction_installment_services.get_transaction_by_installment(
            transaction.parcelamento
        )
        templatetags['transactions'] = transactions
    templatetags['transaction'] = transaction
    set_menu_templatetags(request.user, templatetags)
    return render(request, 'transaction/detail_transaction.html', templatetags)


@login_required
def update_transaction(request, id):
    """
    Atualiza um lançamento existente com base nos dados do formulário.

    Esta view trata as solicitações POST recebidas do formulário de edição de lançamentos. Valida os dados do formulário, atualiza o lançamento existente com base nesses dados e executa verificações de saldo da conta e divisão em parcelas, se aplicável.

    Args:
        request (HttpRequest): O objeto de solicitação HTTP enviado pelo cliente.
        id (int): O ID do lançamento a ser atualizada.

    Returns:
        HttpResponseRedirect: Um redirecionamento para a página de lançamentos do mês atual após a atualização bem-sucedida do lançamento.
    """
    old_transaction = transaction_services.get_transaction_by_id(id, request.user)
    transaction_form = UpdateTransactionForm(request.POST or None, instance=old_transaction)
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
        if transaction_form.cleaned_data['installment_option'] == 'parcelar':
            installment_repository.validate_installment(old_transaction_copy, new_transaction)
            return redirect('get_current_month_transactions')
        else:
            transaction_services.update_transaction(old_transaction, new_transaction)
        return redirect('get_current_month_transactions')
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['transaction_form'] = transaction_form
    templatetags['old_transaction'] = old_transaction
    return render(request, 'transaction/transaction_form.html', templatetags)


@login_required
def delete_transaction(request, id):
    """
    Exclui um lançamento existente.

    Esta view trata as solicitações POST recebidas do formulário de exclusão de lançamentos.
    Exclui o lançamento existente e executa verificações de saldo da conta, se aplicável.

    Args:
        request (HttpRequest): O objeto de solicitação HTTP enviado pelo cliente.
        id (int): O ID do lançamento a ser excluída.

    Returns:
        HttpResponseRedirect: Um redirecionamento para a página de lançamentos do mês atual
        após a exclusão bem-sucedida do lançamento.
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
