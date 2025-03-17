import re
from datetime import date

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator

from statement.forms.general_forms import ExclusionForm
from statement.services.core.account import AccountService
from statement.services.core.card import CardService


class BaseView:
    """
    Classe base para views com operações CRUD padrão.
    """

    actions_list = {
        'create': True,
        'delete': True,
        'detail': True,
        'get_all': True,
        'update': True,
    }
    class_has_user = False
    class_title = False
    column_names = ([],)
    class_form = None
    default_form = True
    model = None
    redirect_url = None
    service = None
    template_is_global = {
        'create': True,
        'delete': True,
        'detail': True,
        'get_all': True,
        'update': True,
    }

    def __init__(self):
        """
        Inicializador da classe
        """
        self.templatetags = {}
        self.snake_case_classname = self._pascal_to_snake()
        self.actions_list = self.actions_list.copy()
        self.template_is_global = self.template_is_global.copy()
        self._context = ''

    @method_decorator(login_required)
    def create(self, request, id=None):
        """
        Cria uma nova instância do modelo.
        """
        self._context = 'create'
        user = self._get_user(request)
        if request.method == 'POST':
            form = self._set_form(request, instance=None)
            if form.is_valid():
                instance = self.service.create(form=form, user=user, id=id)
                self._custom_actions(request=request, form=form, instance=instance)
                return redirect(self.redirect_url)
            else:
                print('Formulário inválido:')
                print(form.errors)
        else:
            form = self._set_form(request, instance=None)
        specific_content = {
            'create': True,  # Define o comportamento do template (create ou update)
        }
        template = self._set_template_by_global_status('create')
        return self._render(request, form, template, specific_content)

    @method_decorator(login_required)
    def get_all(self, request):
        """
        Retorna todas as instâncias do modelo.
        """
        self._context = 'get_all'
        user = self._get_user(request)
        instances = self.service.get_all(user)
        specific_content = {
            'instances': instances,
            'fields': list(map(lambda item: item[0], self.class_form().fields.items())),
        }
        template = self._set_template_by_global_status('get_all')
        return self._render(request, None, template, specific_content)

    @method_decorator(login_required)
    def detail(self, request, id):
        """
        Retorna uma instância específica do modelo.
        """
        self._context = 'detail'
        user = self._get_user(request)
        instance = self.service.get_by_id(id, user)
        additional_context = self._add_context_on_templatetags(request, instance)
        specific_content = {
            'instance': instance,
            **additional_context,
        }
        template = self._set_template_by_global_status('detail')
        return self._render(request, None, template, specific_content)

    @method_decorator(login_required)
    def update(self, request, id):
        """
        Atualiza uma instância existente do modelo.
        """
        self._context = 'update'
        instance = self.service.get_by_id(id)
        form = self._set_form(request, instance)
        if form.is_valid():
            self._custom_actions(request=request, form=form, instance=instance)
            self.service.update(form, instance)
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
        """
        Exclui uma instância do modelo.
        """
        self._context = 'delete'
        instance = self.service.get_by_id(id)
        if request.method == 'POST':
            self._custom_actions(request=request, form=None, instance=instance)
            self.service.delete(instance)
            return redirect(self.redirect_url)
        additional_context = self._add_context_on_templatetags(request, instance)
        specific_content = {
            'delete': True,
            'exclusion_form': ExclusionForm(),
            'instance': instance,
            **additional_context,
        }
        template = self._set_template_by_global_status('delete')
        print(template)
        return self._render(request, None, template, specific_content)

    def _get_user(self, request):
        """
        Retorna o usuário da requisição, se necessário.
        """
        if self.class_has_user:
            return request.user
        return None

    def _render(self, request, form, template, specific_content=False):
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
            'extracts': AccountService.get_all(user),
            'invoices': CardService.get_all(user),
            'class_title': self.class_title,
            'urls': {
                'create': f'create_{self.snake_case_classname}',
                'get_all': f'get_all_{self.snake_case_classname}',
                'detail': f'detail_{self.snake_case_classname}',
                'update': f'update_{self.snake_case_classname}',
                'delete': f'delete_{self.snake_case_classname}',
            },
            'actions_list': self.actions_list,
            'context': self._context,
        }

    def _pascal_to_snake(self):
        """
        Transforma um nome de PascalCase para snake_case
        """
        classname = self.model.__name__
        return re.sub(r'(?<!^)(?=[A-Z])', '_', classname).lower()

    def _set_template_by_global_status(self, method):
        """
        Seta o template de acordo com o status global de cada método
        """
        template = {
            'create': 'form.html',
            'delete': 'detail.html',
            'detail': 'detail.html',
            'get_all': 'list.html',
            'update': 'form.html',
        }
        if self.template_is_global[method]:
            return f'base/{template[method]}'
        return f'{self.snake_case_classname}/{template[method]}'

    def _add_context_on_templatetags(self, request, instance):
        """
        Permite que subclasses adicionem dados extras ao contexto.
        """
        return {}

    def _set_form(self, request, instance):
        """
        Permite que subclasses customizem o formulário
        """
        match self._context:
            case 'create':
                if request.method == 'POST':
                    return self.class_form(request.POST, request.FILES or None)
                return self.class_form()
            case 'update':
                return self.class_form(request.POST or None, request.FILES or None, instance=instance)
            case _:
                raise ValueError('Sem contexto definido.')

    def _custom_actions(self, request, form, instance):
        """
        Permite que a classe filha customize ações ao criar, atualizar ou deletar

        :request (django.http.HttpRequest): - Informações sobre o cabeçalho, método e outros dados da requisição.
        :form (ModelForm): O formulário do modelo da instância.
        :instance: A instância criada, atualizada ou removida no banco de dados.
        """
