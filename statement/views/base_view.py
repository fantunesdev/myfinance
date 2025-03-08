import re
from datetime import date

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.utils.translation import activate

from statement.forms.general_forms import ExclusionForm
from statement.services import account_services, card_services


class BaseView:
    """
    Classe base para views com operações CRUD padrão.
    """
    class_has_user = False
    class_title = False
    form_class = None
    model = None
    service = None
    redirect_url = None

    def __init__(self):
        """
        Inicializador da classe
        """
        self.templatetags = {}
        self.snake_case_classname = self.classname_to_snake_case()

    def _get_user(self, request):
        """
        Retorna o usuário da requisição, se necessário.
        """
        if self.class_has_user:
            return request.user
        return None

    @method_decorator(login_required)
    def create(self, request):
        """
        Cria uma nova instância do modelo.
        """
        user = self._get_user(request)
        if request.method == 'POST':
            form = self.form_class(request.POST, request.FILES)
            if form.is_valid():
                self.service.create(form, user)
                return redirect(self.redirect_url)
        else:
            form = self.form_class()
        return self.render_form(request, form, 'base/form.html')

    @method_decorator(login_required)
    def get_all(self, request):
        """
        Retorna todas as instâncias do modelo.
        """
        user = self._get_user(request)
        instances = self.service.get_all(user)
        specific_content = {
            'instances': instances,
        }
        return self.render_form(request, None, 'list.html', specific_content)

    @method_decorator(login_required)
    def get_by_id(self, request, id):
        """
        Retorna uma instância específica do modelo.
        """
        user = self._get_user(request)
        instance = self.service.get_by_id(id, user)
        specific_content = {
            'instance': instance,
        }
        return self.render_form(request, None, 'detail.html', specific_content)

    @method_decorator(login_required)
    def update(self, request, id):
        """
        Atualiza uma instância existente do modelo.
        """
        instance = self.service.get_by_id(id)
        form = self.form_class(request.POST or None, request.FILES or None, instance=instance)
        if form.is_valid():
            self.service.update(form, instance)
            return redirect(self.redirect_url)
        specific_content = {
            'old_instance': instance,
            'delete_url': f'delete_{self.snake_case_classname}',
        }
        return self.render_form(request, form, 'base/form.html', specific_content)

    @method_decorator(login_required)
    def delete(self, request, id):
        """
        Exclui uma instância do modelo.
        """
        instance = self.service.get_by_id(id)
        if request.method == 'POST':
            self.service.delete(instance)
            return redirect(self.redirect_url)
        instance_attrs = {
            key: value
            for key, value in instance.__dict__.items()
            if not key.startswith('_')
        }
        specific_content = {
            'exclusion_form': ExclusionForm(),
            'instance_attrs': instance_attrs,
        }
        return self.render_form(request, None, 'base/detail.html', specific_content)

    def render_form(self, request, form, template, specific_content=False):
        """
        Renderiza o formulário com o contexto necessário.
        """
        self.__set_context(request.user)

        if form:
            self.templatetags['form'] = form

        if specific_content:
            self.templatetags.update(specific_content or {})

        return render(request, template, self.templatetags)

    def __set_context(self, user):
        """
        Define o contexto padrão para o template.
        """
        self.templatetags = {
            'current_year': date.today().year,
            'current_month': date.today().month,
            'year_month': date.today(),
            'extracts': account_services.get_accounts(user),
            'invoices': card_services.get_cards(user),
            'class_title': self.class_title,
            'snake_case_classname': self.snake_case_classname
        }

    def classname_to_snake_case(self):
        classname = self.model.__name__
        return re.sub(r'(?<!^)(?=[A-Z])', '_', classname).lower()
