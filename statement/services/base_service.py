from django.db import transaction
from django.forms.models import model_to_dict


class BaseService:
    """
    Classe base para manipulação de operações CRUD comuns em modelos.
    """

    model = None
    user_field = 'user'
    parent_service = None
    parent_class_field = None

    @classmethod
    def create(cls, form, user=None, id=None):
        """
        Cria e salva uma instância do modelo.

        :form (ModelForm): Formulário do model da instância.
        :user (models.User): Usuário da requisição
        :id (int): Usado para classes filhas que precisam receber o id da classe mãe.
        """
        instance = form.save(commit=False)
        instance = cls.verify_user_field(instance, user)
        instance.save()
        return instance

    @classmethod
    def get_all(cls, user=None):
        """
        Retorna todas as instâncias filtradas por usuário.
        """
        return cls.filter_by_user(user)

    @classmethod
    def get_by_id(cls, id, user=None):
        """
        Retorna uma instância pelo ID, filtrada por usuário.
        """
        return cls.filter_by_user(user, id=id).get()

    @classmethod
    def update(cls, form, instance):
        """
        Atualiza uma instância com os dados do formulário.
        """
        updated_instance = form.save(commit=False)
        model_fields = [field.name for field in cls.model._meta.fields if field.name != 'id']

        for field in model_fields:
            setattr(instance, field, getattr(updated_instance, field))

        instance.save()
        return instance

    @classmethod
    @transaction.atomic
    def patch(cls, instance, data: dict):
        """
        Atualiza campos específicos de uma instância no banco de dados.

        :param instance: Instância do modelo a ser atualizada.
        :param data: Dicionário contendo os campos e valores a serem atualizados.
        """
        if not isinstance(data, dict):
            raise ValueError('Os dados devem ser um dicionário.')

        for field, value in data.items():
            if hasattr(instance, field):
                setattr(instance, field, value)
            else:
                raise ValueError(f"O campo '{field}' não existe no modelo {cls.model.__name__}.")

        instance.save(update_fields=data.keys())
        return instance

    @classmethod
    def delete(cls, instance):
        """
        Exclui uma instância.
        """
        instance.delete()

    @classmethod
    def verify_user_field(cls, instance, user):
        """
        Atribui o usuário ao campo do modelo, se houver.
        """
        if cls.user_field and hasattr(cls.model, cls.user_field):
            setattr(instance, cls.user_field, user)
        return instance

    @classmethod
    def filter_by_user(cls, user, id=None):
        """
        Filtra instâncias pelo usuário e, opcionalmente, pelo ID.
        """
        filters = {}

        if id:
            filters['id'] = id

        if cls.user_field and hasattr(cls.model, cls.user_field) and user:
            filters[cls.user_field] = user

        return cls.model.objects.filter(**filters)

    @staticmethod
    def instance_to_form(instance, form):
        """
        Transforma uma instância em um formulário.

        :instance (models.Instance): A instância do modelo a ser convertida.
        :form (ModelForm): O formulário do modelo da instância.

        :Example: cls.instance_to_form(transaction, TransactionForm)
        """
        instance_dict = model_to_dict(instance)
        instance_dict.pop('id')
        return form(instance_dict)
