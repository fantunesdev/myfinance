from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from statement.views.base_view import BaseView


class InvestmentCrudView(BaseView):
    class_has_user = True
    show_duplicate_checker = False

    @staticmethod
    def _get_wallet(request):
        from investments.services.transaction import InvestmentTransactionService

        try:
            return InvestmentTransactionService.get_or_create_default_wallet(request.user)
        except ValidationError as error:
            messages.error(request, ' '.join(error.messages))
            return None

    def _set_form(self, request, instance):
        match self._context:
            case 'create':
                if request.method == 'POST':
                    return self.class_form(request.POST, request.FILES or None, user=request.user)
                return self.class_form(user=request.user)
            case 'update':
                return self.class_form(
                    request.POST or None, request.FILES or None, instance=instance, user=request.user
                )
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
            try:
                self.service.update(form, form.instance)
            except ValidationError as error:
                form.add_error(None, error.messages)
            else:
                return redirect(self.redirect_url)
        additional_context = self._add_context_on_templatetags(request, instance)
        specific_content = {
            'old_instance': instance,
            'update': True,
            **additional_context,
        }
        template = self._set_template_by_global_status('update')
        return self._render(request, form, template, specific_content)

    def _preserve_unrendered_fields_after_validation(self, form, original_instance):
        # A missing field is different from a field explicitly cleared by the user.
        for name in form.fields:
            if name not in form.data:
                setattr(form.instance, name, getattr(original_instance, name))

    @staticmethod
    def _perform_movement(form, action, **kwargs):
        try:
            action(**kwargs)
        except ValidationError as error:
            form.add_error(None, error.messages)
            return False
        return True

    @method_decorator(login_required)
    def delete(self, request, id):
        self._context = 'delete'
        instance = self.service.get_by_id(id, request.user)
        return super().delete(request, instance.id)
