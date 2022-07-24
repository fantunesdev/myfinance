from django.shortcuts import redirect, render

from balanco.entidades.movimentacao import Movimentacao
from balanco.forms import parcelamento_form
from balanco.forms.general_forms import ExclusaoForm
from balanco.repositorios import parcelamento_repositorio
from balanco.services import parcelamento_service, movimentacao_service, conta_service
from balanco.views.movimentacao_view import template_tags


def detalhar_parcelamento(request, id):
    parcelamento = parcelamento_service.listar_parcelamento_id(id, request.user)
    template_tags['movimentacoes'] = movimentacao_service.listar_movimentacoes_parcelamento(parcelamento)
    template_tags['parcelamento'] = parcelamento
    template_tags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'parcelamento/detalhar_parcelamento.html', template_tags)


def editar_parcelamento(request, id):
    parcelamento = parcelamento_service.listar_parcelamento_id(id, request.user)
    movimentacoes = movimentacao_service.listar_movimentacoes_parcelamento(parcelamento)
    form_parcelamento = parcelamento_form.ParcelamentoForm(request.POST or None, instance=movimentacoes[0])
    if form_parcelamento.is_valid():
        movimentacao_nova = Movimentacao(
            data_lancamento=form_parcelamento.cleaned_data['data_lancamento'],
            data_efetivacao=None,
            conta=form_parcelamento.cleaned_data['conta'],
            cartao=form_parcelamento.cleaned_data['cartao'],
            categoria=form_parcelamento.cleaned_data['categoria'],
            subcategoria=form_parcelamento.cleaned_data['subcategoria'],
            descricao=form_parcelamento.cleaned_data['descricao'],
            valor=form_parcelamento.cleaned_data['valor'],
            numero_parcelas=form_parcelamento.cleaned_data['numero_parcelas'],
            pagas=0,
            fixa=form_parcelamento.cleaned_data['fixa'],
            anual=form_parcelamento.cleaned_data['anual'],
            moeda=form_parcelamento.cleaned_data['moeda'],
            observacao=form_parcelamento.cleaned_data['observacao'],
            lembrar=form_parcelamento.cleaned_data['lembrar'],
            tipo=form_parcelamento.cleaned_data['tipo'],
            efetivado=form_parcelamento.cleaned_data['efetivado'],
            tela_inicial=form_parcelamento.cleaned_data['tela_inicial'],
            usuario=request.user,
            parcelamento=parcelamento
        )
        reordenar_datas_lancamento = form_parcelamento.cleaned_data['reordenar_datas_lancamento']
        parcelamento_repositorio.editar_parcelamento(movimentacoes, movimentacao_nova, reordenar_datas_lancamento)
        return redirect('listar_mes_atual')
    template_tags['movimentacoes'] = movimentacoes
    template_tags['parcelamento'] = parcelamento
    template_tags['contas'] = conta_service.listar_contas(request.user)
    template_tags['form_parcelamento'] = form_parcelamento
    return render(request, 'parcelamento/detalhar_parcelamento.html', template_tags)


def adiantar_parcelas(request, id):
    parcelamento = parcelamento_service.listar_parcelamento_id(id, request.user)
    parcelas = movimentacao_service.listar_movimentacoes_parcelamento(parcelamento)
    if request.method == 'POST':
        form_parcelamento = parcelamento_form.AdiantarParcelaForm(request.POST)
        if form_parcelamento.is_valid():
            quantidade = form_parcelamento.cleaned_data['quantidade']
            data_inicial = form_parcelamento.cleaned_data['data_inicial']
            parcelamento_repositorio.adiantar_parcelas(quantidade, data_inicial, parcelas)
            return redirect('listar_mes_atual')
    else:
        form_parcelamento = parcelamento_form.AdiantarParcelaForm()
    template_tags['parcelas'] = parcelas
    template_tags['parcelamento'] = parcelamento
    template_tags['form_parcelamento'] = form_parcelamento
    return render(request, 'parcelamento/adiantar_parcelas.html', template_tags)


def remover_parcelamento(request, id):
    parcelamento = parcelamento_service.listar_parcelamento_id(id, request.user)
    movimentacoes = movimentacao_service.listar_movimentacoes_parcelamento(parcelamento)
    form_exclusao = ExclusaoForm()
    if request.POST.get('confirmacao'):
        parcelamento_service.remover_parcelamento(parcelamento)
        return redirect('listar_mes_atual')

    template_tags['form_exclusao'] = form_exclusao
    template_tags['parcelamento'] = parcelamento
    template_tags['movimentacoes'] = movimentacoes
    template_tags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'parcelamento/detalhar_parcelamento.html', template_tags)


def remover_parcela(request, id):
    movimentacao = movimentacao_service.listar_movimentacao_id(id, request.user)
    movimentacoes = movimentacao_service.listar_movimentacoes_parcelamento(movimentacao.parcelamento)
    form_exclusao = ExclusaoForm()
    if request.POST.get('confirmacao'):
        movimentacao.numero_parcelas -= 1
        parcelamento_repositorio.editar_parcelamento(movimentacoes, movimentacao)
        return redirect('listar_mes_atual')
    template_tags['form_exclusao'] = form_exclusao
    template_tags['movimentacao'] = movimentacao
    template_tags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'movimentacao/detalhar_movimentacao.html', template_tags)
