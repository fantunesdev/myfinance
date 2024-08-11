from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from statement.entities.card import Card
from statement.forms.card_form import CardForm
from statement.forms.general_forms import ExclusionForm
from statement.repositories.templatetags_repository import set_menu_templatetags, set_templatetags
from statement.services import account_services, card_services


@login_required
def create_card(request):
    if request.method == 'POST':
        card_form = CardForm(request.POST, request.FILES)
        if card_form.is_valid():
            card = Card(
                flag=card_form.cleaned_data['flag'],
                icon=card_form.cleaned_data['icon'],
                description=card_form.cleaned_data['description'],
                limits=card_form.cleaned_data['limits'],
                account=card_form.cleaned_data['account'],
                expiration_day=card_form.cleaned_data['expiration_day'],
                closing_day=card_form.cleaned_data['closing_day'],
                home_screen=card_form.cleaned_data['home_screen'],
                user=request.user,
            )
            card_services.create_card(card)
            return redirect('setup_settings')
    else:
        card_form = CardForm()
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['card_form'] = card_form
    return render(request, 'card/card_form.html', templatetags)


@login_required
def update_card(request, id):
    old_card = card_services.get_card_by_id(id, request.user)
    card_form = CardForm(request.POST or None, request.FILES or None, instance=old_card)
    if card_form.is_valid():
        new_card = Card(
            flag=card_form.cleaned_data['flag'],
            icon=card_form.cleaned_data['icon'],
            description=card_form.cleaned_data['description'],
            limits=card_form.cleaned_data['limits'],
            account=card_form.cleaned_data['account'],
            expiration_day=card_form.cleaned_data['expiration_day'],
            closing_day=card_form.cleaned_data['closing_day'],
            home_screen=card_form.cleaned_data['home_screen'],
            user=request.user,
        )
        card_services.update_card(old_card, new_card)
        return redirect('setup_settings')
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['old_card'] = old_card
    templatetags['card_form'] = card_form
    return render(request, 'card/card_form.html', templatetags)


@login_required
def delete_card(request, id):
    card = card_services.get_card_by_id(id, request.user)
    exclusion_form = ExclusionForm()
    if request.POST.get('confirmation'):
        card_services.delete_card(card)
        return redirect('setup_settings')
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['card'] = card
    templatetags['exclusion_form'] = exclusion_form
    return render(request, 'card/exclusion_confirmation_card.html', templatetags)
