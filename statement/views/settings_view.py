from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render, redirect

from balanco.models import ContaTipo, Moeda, Antecipation, Categoria, Parcelamento, Banco, Bandeira, Conta, Cartao, \
    Subcategoria, Movimentacao
from statement.models import Bank, Account, AccountType, Flag, Card, Installment, Category, Subcategory, Currency, \
    NextMonthView, Transaction
from statement.repositories.templatetags_repository import set_templatetags, set_menu_templatetags
from statement.services import next_month_view_services, bank_services, account_services, card_services, \
    category_services, subcategory_services, flag_services, installment_services, transaction_services


def setup_settings(request):
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['accounts'] = account_services.get_accounts(request.user)
    templatetags['next_month_view'] = next_month_view_services.get_next_month_view_by_user(request.user)
    templatetags['banks'] = bank_services.get_banks()
    templatetags['flags'] = flag_services.get_flags()
    templatetags['cards'] = card_services.get_cards(request.user)
    templatetags['categories'] = category_services.get_categories(request.user)
    templatetags['subcategories'] = subcategory_services.get_subcategories(request.user)
    return render(request, 'general/setup_settings.html', templatetags)


def importar_banco(request):
    user = request.user
    for i in Bandeira.objects.all():
        Flag.objects.create(
            id=i.id,
            description=i.descricao,
            icon=i.icone
        )

    for i in Banco.objects.all():
        Bank.objects.create(
            id=i.id,
            description=i.descricao,
            code=i.codigo,
            icon=i.icone
        )

    for i in Parcelamento.objects.all():
        Installment.objects.create(
            id=i.id,
            release_date=i.data_lancamento,
            description=i.descricao,
            user=request.user
        )

    for i in Categoria.objects.all():
        Category.objects.create(
            id=i.id,
            type=i.tipo,
            description=i.descricao,
            icon=i.icone,
            color=i.cor,
            ignore=False,
            user=request.user
        )

    for i in ContaTipo.objects.all():
        AccountType.objects.create(
            id=i.id,
            description=i.descricao
        )

    for i in Moeda.objects.all():
        Currency.objects.create(
            id=i.id,
            description=i.descricao,
            symbol=i.simbolo
        )

    for i in Antecipation.objects.all():
        NextMonthView.objects.create(
            id=i.id,
            day=i.day,
            active=i.active,
            user=user
        )

    for i in Conta.objects.all():
        bank = Bank.objects.get(id=i.banco.id)
        type = AccountType.objects.get(id=1)
        Account.objects.create(
            id=i.id,
            bank=bank,
            branch=i.agencia,
            number=i.numero,
            balance=i.saldo,
            limits=i.limite,
            type=type,
            home_screen=i.tela_inicial,
            user=i.usuario
        )

    for i in Cartao.objects.all():
        flag = flag_services.get_flag_by_id(i.bandeira.id)
        account_db = account_services.get_account_by_id(1, request.user)
        Card.objects.create(
            id=i.id,
            flag=flag,
            icon=i.icone,
            description=i.descricao,
            limits=i.limite,account=account_db,
            expiration_day=i.vencimento,
            closing_day=i.fechamento,
            home_screen=i.tela_inicial,
            user=request.user
        )

    for i in Subcategoria.objects.all():
        category = category_services.get_category_by_id(i.categoria.id, request.user)
        Subcategory.objects.create(
            id=i.id,
            description=i.descricao,
            category=category,
            user=request.user
        )

    for i in Movimentacao.objects.all():
        try:
            account = account_services.get_account_by_id(i.conta.id, request.user)
        except ObjectDoesNotExist:
            account = None
        except AttributeError:
            account = None

        try:
            card = card_services.get_card_by_id(i.cartao.id, request.user)
        except ObjectDoesNotExist:
            card = None
        except AttributeError:
            card = None

        try:
            installment = installment_services.get_installment_by_id(i.parcelamento.id, request.user)
        except ObjectDoesNotExist :
            installment = None
        except AttributeError:
            installment = None

        category = category_services.get_category_by_id(i.categoria.id, request.user)
        subcategory = subcategory_services.get_subcategory_by_id(i.subcategoria.id, request.user)

        new_transaction = Transaction.objects.create(
            release_date=i.data_lancamento,
            payment_date=i.data_efetivacao,
            account=account,
            card=card,
            category=category,
            subcategory=subcategory,
            description=i.descricao,
            value=i.valor,
            installments_number=i.numero_parcelas,
            paid=i.pagas,
            fixed=i.fixa,
            annual=i.anual,
            currency=Currency.objects.get(id='BRL'),
            observation=i.observacao,
            remember=i.lembrar,
            type=i.tipo,
            effected=i.efetivado,
            home_screen=i.tela_inicial,
            user=request.user,
            installment=installment
        )

    templatetags = set_templatetags()
    templatetags['next_month_view'] = next_month_view_services.get_next_month_view_by_user(request.user)
    templatetags['banks'] = bank_services.get_banks()
    templatetags['flags'] = flag_services.get_flags()
    templatetags['cards'] = card_services.get_cards(request.user)
    templatetags['categories'] = category_services.get_categories(request.user)
    templatetags['subcategories'] = subcategory_services.get_subcategories(request.user)
    return render(request, 'general/settings.html', templatetags)
