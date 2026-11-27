from types import SimpleNamespace

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from login.models import Profile
from statement.forms.subcategory_preferences import SubcategoryPreferencesForm
from statement.models import Subcategory


@login_required
def edit_subcategory_preferences(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    initial = {'hidden_subcategories': list(profile.disabled_subcategories.values_list('pk', flat=True))}
    form = SubcategoryPreferencesForm(request.POST if request.method == 'POST' else None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        profile.disabled_subcategories.set(form.cleaned_data['hidden_subcategories'])
        messages.success(request, 'Suas preferências de subcategorias foram salvas.')
        return redirect('get_profile')

    options = [
        SimpleNamespace(subcategory=subcategory, subcategory_id=subcategory.pk)
        for subcategory in Subcategory.objects.select_related('category').order_by(
            'category__description',
            'description',
        )
    ]
    selected_ids = set(map(str, form['hidden_subcategories'].value() or []))
    return render(
        request,
        'subcategory_preferences/form.html',
        {
            'class_title': 'Subcategorias que uso',
            'form': form,
            'options': options,
            'selected': [option for option in options if str(option.subcategory_id) in selected_ids],
            'chart': {'field': 'personal-subcategories'},
        },
    )
