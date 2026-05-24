from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.utils.decorators import method_decorator

from statement.views.base_view import BaseView


class InvestmentCrudView(BaseView):
    class_has_user = True

    def _set_form(self, request, instance):
        match self._context:
            case 'create':
                if request.method == 'POST':
                    return self.class_form(request.POST, request.FILES or None, user=request.user)
                return self.class_form(user=request.user)
            case 'update':
                return self.class_form(request.POST or None, request.FILES or None, instance=instance, user=request.user)
            case _:
                raise ValueError('Sem contexto definido.')

    @method_decorator(login_required)
    def update(self, request, id):
        self._context = 'update'
        instance = self.service.get_by_id(id, request.user)
        form = self._set_form(request, instance)
        original_instance = type(instance).objects.get(pk=instance.pk)
        if form.is_valid():
            self._preserve_unrendered_fields_after_validation(form, original_instance)
            self._custom_actions(request=request, form=form, instance=form.instance)
            self.service.update(form, form.instance)
            return redirect(self.redirect_url)
        additional_context = self._add_context_on_templatetags(request, instance)
        specific_content = {
            'old_instance': instance,
            'update': True,
            **additional_context,
        }
        template = self._set_template_by_global_status('update')
        return self._render(request, form, template, specific_content)

    @method_decorator(login_required)
    def delete(self, request, id):
        self._context = 'delete'
        instance = self.service.get_by_id(id, request.user)
        return super().delete(request, instance.id)
