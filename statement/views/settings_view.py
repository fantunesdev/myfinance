from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render, redirect

from balanco.services import banco_service, bandeira_service, conta_service, categoria_service, subcategoria_service, \
    movimentacao_service, cartao_service, parcelamento_service
from statement.entities.account import Account
from statement.entities.bank import Bank
from statement.entities.card import Card
from statement.entities.category import Category
from statement.entities.flag import Flag
from statement.entities.installment import Installment
from statement.entities.subcategory import Subcategory
from statement.entities.transaction import Transaction
from statement.models import AccountType, Currency
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
    bancos = banco_service.listar_bancos()
    bandeiras = bandeira_service.listar_bandeiras()
    contas = conta_service.listar_contas(request.user)
    cartoes = cartao_service.listar_cartoes(request.user)
    categorias = categoria_service.listar_categorias(request.user)
    subcategorias = subcategoria_service.listar_subcategorias(request.user)
    movimentacoes = movimentacao_service.listar_movimentacoes(request.user)
    parcelamentos = parcelamento_service.listar_parcelamentos(request.user)

    for i in bancos:
        new_bank = Bank(description=i.descricao, code=i.codigo, icon=i.icone)
        bank_services.create_bank(new_bank)

    for i in bandeiras:
        new_flag = Flag(description=i.descricao, icon=i.icone)
        flag_services.create_flag(new_flag)

    for i in contas:
        bank = bank_services.get_bank_by_id(i.banco.id)
        type = AccountType.objects.get(id=1)
        new_account = Account(bank=bank, branch=i.agencia, number=i.numero, balance=i.saldo, limits=i.limite, type=type, home_screen=i.tela_inicial, user=i.usuario)
        account_services.create_account(new_account)

    for i in cartoes:
        flag = flag_services.get_flag_by_id(i.bandeira.id)
        account_db = account_services.get_account_by_id(1, request.user)
        new_card = Card(flag=flag,icon=i.icone,description=i.descricao,limits=i.limite,account=account_db,expiration_day=i.vencimento,closing_day=i.fechamento,home_screen=i.tela_inicial,user=request.user)
        card_services.create_card(new_card)

    for i in parcelamentos:
        new_installment = Installment(release_date=i.data_lancamento,description=i.descricao,user=request.user)
        installment_services.create_installment(new_installment)

    for i in categorias:
        new_category = Category(type=i.tipo, description=i.descricao, icon=i.icone, color=i.cor, ignore=False, user=request.user)
        category_services.create_category(new_category)

    for i in subcategorias:
        category = category_services.get_category_by_id(i.categoria.id, request.user)
        new_subcategory = Subcategory(description=i.descricao, category=category, user=request.user)
        subcategory_services.create_subcategory(new_subcategory)

    for i in movimentacoes:
        try:
            account = account_services.get_account_by_id(i.conta.id, request.user)
        except AttributeError:
            account = None

        try:
            card = card_services.get_card_by_id(i.cartao.id, request.user)
        except ObjectDoesNotExist:
            card = None
        except AttributeError:
            card = None

        category = category_services.get_category_by_id(i.categoria.id, request.user)
        subcategory = subcategory_services.get_subcategory_by_id(i.subcategoria.id, request.user)
        try:
            installment = installment_services.get_installment_by_id(i.parcelamento.id, request.user)
        except AttributeError:
            installment = None
        except ObjectDoesNotExist:
            card = None

        new_transaction = Transaction(
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
        transaction_services.create_transaction(new_transaction)

    templatetags = set_templatetags()
    templatetags['next_month_view'] = next_month_view_services.get_next_month_view_by_user(request.user)
    templatetags['banks'] = bank_services.get_banks()
    templatetags['flags'] = flag_services.get_flags()
    templatetags['cards'] = card_services.get_cards(request.user)
    templatetags['categories'] = category_services.get_categories(request.user)
    templatetags['subcategories'] = subcategory_services.get_subcategories(request.user)
    return render(request, 'general/settings.html', templatetags)
