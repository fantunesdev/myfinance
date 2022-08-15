from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from balanco.entidades.cartao import Cartao
from balanco.forms.general_forms import ExclusaoForm
from balanco.services import cartao_service, conta_service
from balanco.views.movimentacao_view import templatetags
from balanco.forms.cartao_form import CartaoForm


@login_required
def cadastrar_cartao(request):
    if request.method == 'POST':
        form_cartao = CartaoForm(request.POST, request.FILES)
        if form_cartao.is_valid():
            cartao = Cartao(
                bandeira=form_cartao.cleaned_data['bandeira'],
                icone=form_cartao.cleaned_data['icone'],
                descricao=form_cartao.cleaned_data['descricao'],
                limite=form_cartao.cleaned_data['limite'],
                conta=form_cartao.cleaned_data['conta'],
                vencimento=form_cartao.cleaned_data['vencimento'],
                fechamento=form_cartao.cleaned_data['fechamento'],
                tela_inicial=form_cartao.cleaned_data['tela_inicial'],
                usuario=request.user
            )
            cartao_service.cadastrar_cartao(cartao)
            return redirect('listar_mes_atual')
    else:
        form_cartao = CartaoForm()
    templatetags['form_cartao'] = form_cartao
    templatetags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'cartao/form_cartao.html', templatetags)


@login_required
def listar_cartoes(request):
    templatetags['cartoes'] = cartao_service.listar_cartoes(request.user)
    templatetags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'cartao/listar.html', templatetags)


@login_required
def editar_cartao(request, id):
    cartao_antigo = cartao_service.listar_cartao_id(id, request.user)
    form_cartao = CartaoForm(request.POST or None, request.FILES or None, instance=cartao_antigo)
    if form_cartao.is_valid():
        cartao_novo = Cartao(
                bandeira=form_cartao.cleaned_data['bandeira'],
                icone=form_cartao.cleaned_data['icone'],
                descricao=form_cartao.cleaned_data['descricao'],
                limite=form_cartao.cleaned_data['limite'],
                conta=form_cartao.cleaned_data['conta'],
                vencimento=form_cartao.cleaned_data['vencimento'],
                fechamento=form_cartao.cleaned_data['fechamento'],
                tela_inicial=form_cartao.cleaned_data['tela_inicial'],
                usuario=request.user
            )
        print(cartao_novo.icone)
        cartao_service.editar_cartao(cartao_antigo, cartao_novo)
        return redirect('listar_mes_atual')
    templatetags['cartao_antigo'] = cartao_antigo
    templatetags['form_cartao'] = form_cartao
    templatetags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'cartao/editar.html', templatetags)


@login_required
def remover_cartao(request, id):
    cartao = cartao_service.listar_cartao_id(id, request.user)
    form_exclusao = ExclusaoForm()
    if request.POST.get('confirmacao'):
        cartao_service.remover_cartao(cartao)
        return redirect('listar_mes_atual')
    templatetags['cartao'] = cartao
    templatetags['form_exclusao'] = form_exclusao
    templatetags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'cartao/confirma_exclusao.html', templatetags)
