class BaseService:
    model = None
    user_field = 'user'

    @classmethod
    def create(cls, form, user=None):
        instance = form.save(commit=False)
        instance = cls.verify_user_field(instance, user)
        instance.save()
        return instance

    @classmethod
    def get_all(cls, user=None):
        return cls.filter_by_user(user)

    @classmethod
    def get_by_id(cls, id, user=None):
        return cls.filter_by_user(user, id=id).get()

    @classmethod
    def update(cls, form, instance):
        updated_instance = form.save(commit=False)
        model_fields = [field.name for field in cls.model._meta.fields if field.name != 'id']

        for field in model_fields:
            setattr(instance, field, getattr(updated_instance, field))

        instance.save()
        return instance

    @classmethod
    def delete(cls, instance):
        instance.delete()

    @classmethod
    def verify_user_field(cls, instance, user):
        """
        Define o usuário no objeto se o modelo possuir um campo de usuário.
        """
        if cls.user_field and hasattr(cls.model, cls.user_field):
            setattr(instance, cls.user_field, user)
        return instance

    @classmethod
    def filter_by_user(cls, user, id=None):
        """
        Filtra pelo usuário se o modelo possuir um campo de usuário.
        Se `id` for passado, também filtra pelo id.
        """
        filters = {}

        if id:
            filters['id'] = id

        if cls.user_field and hasattr(cls.model, cls.user_field) and user:
            filters[cls.user_field] = user

        return cls.model.objects.filter(**filters)
