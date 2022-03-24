from datetime import date

from django.shortcuts import redirect, render

from balanco.entidades.movimentacao import Movimentacao
from balanco.forms.general_form import ExclusaoForm
from balanco.forms.movimentacao_form import MovimentacaoSaidaForm, MovimentacaoEntradaForm
from balanco.services import movimentacao_service


template_tags = {
    'ano_atual': date.today().year,
    'mes_atual': date.today().month
}


def cadastrar_movimentacao(request, tipo):
    if tipo == 'entrada':
        tipo = 0
        form = lambda *args: MovimentacaoEntradaForm(*args)
    else:
        tipo = 1
        form = lambda *args: MovimentacaoSaidaForm(*args)

    if request.method == 'POST':
        form_movimentacao = form(request.POST)
        if form_movimentacao.is_valid():
            movimentacao = Movimentacao(
                valor=form_movimentacao.cleaned_data['valor'],
                data=form_movimentacao.cleaned_data['data'],
                repetir=form_movimentacao.cleaned_data['repetir'],
                parcelas=form_movimentacao.cleaned_data['parcelas'],
                descricao=form_movimentacao.cleaned_data['descricao'],
                categoria=form_movimentacao.cleaned_data['categoria'],
                conta=form_movimentacao.cleaned_data['conta'],
                fixa=form_movimentacao.cleaned_data['fixa'],
                moeda=form_movimentacao.cleaned_data['moeda'],
                observacao=form_movimentacao.cleaned_data['observacao'],
                lembrar=form_movimentacao.cleaned_data['lembrar'],
                tipo=tipo,
                efetivado=form_movimentacao.cleaned_data['efetivado']
            )
            movimentacao_service.cadastrar_movimentacao(movimentacao)
            return redirect('listar_movimentacoes')
    else:
        form_movimentacao = form()
    template_tags['form_movimentacao'] = form_movimentacao
    return render(request, 'movimentacao/form_movimentacao.html', template_tags)


def listar_movimentacoes(request):
    movimentacoes = movimentacao_service.listar_movimentacoes()
    template_tags['movimentacoes'] = movimentacoes
    return render(request, 'movimentacao/listar.html', template_tags)


def editar_movimentacao(request, id):
    movimentacao_antiga = movimentacao_service.listar_movimentacao_id(id)
    if movimentacao_antiga.tipo == 0:
        form_movimentacao = MovimentacaoEntradaForm(request.POST or None, instance=movimentacao_antiga)
    else:
        form_movimentacao = MovimentacaoSaidaForm(request.POST or None, instance=movimentacao_antiga)
    if form_movimentacao.is_valid():
        movimentacao_nova = Movimentacao(
            valor=form_movimentacao.cleaned_data['valor'],
            data=form_movimentacao.cleaned_data['data'],
            repetir=form_movimentacao.cleaned_data['repetir'],
            parcelas=form_movimentacao.cleaned_data['parcelas'],
            descricao=form_movimentacao.cleaned_data['descricao'],
            categoria=form_movimentacao.cleaned_data['categoria'],
            conta=form_movimentacao.cleaned_data['conta'],
            fixa=form_movimentacao.cleaned_data['fixa'],
            moeda=form_movimentacao.cleaned_data['moeda'],
            observacao=form_movimentacao.cleaned_data['observacao'],
            lembrar=form_movimentacao.cleaned_data['lembrar'],
            tipo=movimentacao_antiga.tipo,
            efetivado=form_movimentacao.cleaned_data['efetivado']
        )
        movimentacao_service.editar_movimentacao(movimentacao_antiga, movimentacao_nova)
        return redirect('listar_movimentacoes')
    template_tags['form_movimentacao'] = form_movimentacao
    template_tags['movimentacao_antiga'] = movimentacao_antiga
    return render(request, 'movimentacao/editar.html', template_tags)


def remover_movimentacao(request, id):
    movimentacao = movimentacao_service.listar_movimentacao_id(id)
    form_exclusao = ExclusaoForm()
    if request.POST.get('confirmacao'):
        movimentacao_service.remover_movimentacao(movimentacao)
        return redirect('listar_movimentacoes')
    template_tags['form_exclusao'] = form_exclusao
    template_tags['movimentacao'] = movimentacao
    return render(request, 'movimentacao/confirma_exclusao.html', template_tags)