from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from statement.forms.fuel_tracking_form import FuelTrackingForm
from statement.services.fuel_tracking import FuelTrackingService


@login_required
def edit_fuel_tracking(request):
    """Renderiza e processa o formulário de configuração de combustível no perfil."""
    if request.method == 'POST':
        form = FuelTrackingForm(request.POST)
        if form.is_valid():
            form.save(request.user)
            return redirect('get_profile')
    else:
        fuel_tracking = FuelTrackingService.get(request.user)
        initial = {}
        if fuel_tracking:
            initial = {
                'active': fuel_tracking.active,
                'subcategory': fuel_tracking.subcategory,
            }
        form = FuelTrackingForm(initial=initial)

    context = {
        'form': form,
        'class_title': 'Configuração - Combustível',
        'create': False,
        'update': False,
    }
    return render(request, 'base/form.html', context)
