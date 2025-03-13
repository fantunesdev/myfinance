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
