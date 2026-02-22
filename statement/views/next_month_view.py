from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from statement.forms.next_month_view_form import NextMonthViewForm
from statement.services.next_month_view import NextMonthViewService


@login_required
def edit_next_month_view(request):
    """Renderiza e processa o formulário de configuração do Next Month View no perfil."""
    if request.method == 'POST':
        form = NextMonthViewForm(request.POST)
        if form.is_valid():
            form.save(request.user)
            return redirect('get_profile')
    else:
        nm = NextMonthViewService.get(request.user)
        initial = {}
        if nm:
            initial = {'day': nm.day, 'active': nm.active}
        form = NextMonthViewForm(initial=initial)

    context = {
        'form': form,
        'class_title': 'Configuração - Próximo Mês',
        'create': False,
        'update': False,
    }
    return render(request, 'base/form.html', context)
