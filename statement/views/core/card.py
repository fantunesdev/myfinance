from django.shortcuts import redirect

from statement.forms.core.card import CardForm, CardNumberFormSet
from statement.models import Card
from statement.services.core.card import CardService
from statement.views.base_view import BaseView


class CardView(BaseView):
    """
    View responsável pela gestão dos cartões
    """

    class_has_user = True
    class_title = 'Cartão'
    class_form = CardForm
    model = Card
    service = CardService
    redirect_url = 'setup_settings'
    template_is_global = {
        'create': False,
        'delete': True,
        'detail': True,
        'get_all': True,
        'update': False,
    }

    def create(self, request, id=None):
        """
        Cria uma nova instância do cartão com seus números.
        """
        self._context = 'create'
        user = self._get_user(request)
        
        if request.method == 'POST':
            form = self._set_form(request, instance=None)
            formset = CardNumberFormSet(request.POST, instance=None)
            
            if form.is_valid() and formset.is_valid():
                instance = form.save(commit=False)
                instance.user = user
                instance.save()
                
                # Associa o cartão ao formset antes de salvar
                formset.instance = instance
                formset.save()
                
                self._custom_actions(request=request, form=form, instance=instance)
                return redirect(self.redirect_url)
            else:
                print('Formulário ou formset inválido:')
                if form.errors:
                    print('Erros do formulário:', form.errors)
                if formset.errors:
                    print('Erros do formset:', formset.errors)
        else:
            form = self._set_form(request, instance=None)
            formset = CardNumberFormSet(instance=None)
        
        specific_content = {
            'create': True,
            'formset': formset,
        }
        template = self._set_template_by_global_status('create')
        return self._render(request, form, template, specific_content)

    def update(self, request, id):
        """
        Atualiza uma instância existente do cartão com seus números.
        """
        self._context = 'update'
        instance = self.service.get_by_id(id)
        original_instance = type(instance).objects.get(pk=instance.pk)
        
        if request.method == 'POST':
            form = self._set_form(request, instance)
            formset = CardNumberFormSet(request.POST, instance=instance)
            
            if form.is_valid() and formset.is_valid():
                self._preserve_unrendered_fields_after_validation(form, original_instance)
                self._custom_actions(request=request, form=form, instance=form.instance)
                self.service.update(form, form.instance)
                formset.save()
                return redirect(self.redirect_url)
            else:
                print('Formulário ou formset inválido:')
                if form.errors:
                    print('Erros do formulário:', form.errors)
                if formset.errors:
                    print('Erros do formset:', formset.errors)
        else:
            form = self._set_form(request, instance)
            formset = CardNumberFormSet(instance=instance)
        
        additional_context = self._add_context_on_templatetags(request, instance)
        specific_content = {
            'old_instance': instance,
            'update': True,
            'formset': formset,
            **additional_context,
        }
        template = self._set_template_by_global_status('update')
        return self._render(request, form, template, specific_content)
