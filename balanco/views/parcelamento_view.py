from django.shortcuts import redirect, render

from balanco.forms.general_forms import ExclusaoForm
from balanco.services import parcelamento_service, movimentacao_service, conta_service
from balanco.views.movimentacao_view import template_tags


def remover_parcelamento(request, id):
    parcelamento = parcelamento_service.listar_parcelamento_id(id, request.user)
    movimentacoes = movimentacao_service.listar_movimentacoes_parcelamento(parcelamento)
    form_exclusao = ExclusaoForm()
    if request.POST.get('confirmacao'):
        parcelamento_service.remover_parcelamento(parcelamento)
        return redirect('listar_mes_atual')

    template_tags['form_exclusao'] = form_exclusao
    template_tags['movimentacoes'] = movimentacoes
    template_tags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'parcelamento/detalhar_parcelamento.html', template_tags)
