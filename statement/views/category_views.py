from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from ..forms.category_form import CategoryForm
from ..forms.general_forms import ExclusionForm
from ..models import Category
from ..repositories.templatetags_repository import set_templatetags, set_menu_templatetags
from ..services import category_services, account_services, card_services


@login_required
def create_category(request):
    if request.method == 'POST':
        category_form = CategoryForm(request.POST, request.FILES)
        if category_form.is_valid():
            new_category = Category(
                type=category_form.cleaned_data['type'],
                description=category_form.cleaned_data['description'],
                color=category_form.cleaned_data['color'],
                icon=category_form.cleaned_data['icon'],
                ignore=category_form.cleaned_data['ignore'],
                user=request.user
            )
            category_services.create_category(new_category)
            return redirect('setup_settings')
    else:
        category_form = CategoryForm()
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['category_form'] = category_form
    return render(request, 'category/category_form.html', templatetags)


@login_required
def update_category(request, id):
    old_category = category_services.get_category_by_id(id, request.user)
    category_form = CategoryForm(request.POST or None, request.FILES or None, instance=old_category)
    if category_form.is_valid():
        new_category = Category(
            type=category_form.cleaned_data['type'],
            description=category_form.cleaned_data['description'],
            color=category_form.cleaned_data['color'],
            icon=category_form.cleaned_data['icon'],
            ignore=category_form.cleaned_data['ignore'],
            user=request.user
        )
        category_services.update_category(old_category, new_category)
        return redirect('setup_settings')
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['category_form'] = category_form
    templatetags['old_category'] = old_category
    return render(request, 'category/category_form.html', templatetags)


@login_required
def delete_category(request, id):
    category = category_services.get_category_by_id(id, request.user)
    if request.method == 'POST':
        category_services.delete_category(category)
        return redirect('setup_settings')
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['category'] = category
    templatetags['exclusion_form'] = ExclusionForm()
    return render(request, 'category/exclusion_confirmation_category.html', templatetags)
