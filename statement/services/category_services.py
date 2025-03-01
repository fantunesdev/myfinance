from statement.models import Category


class CategoryServices:
    """
    Serviço para gerenciar categorias financeiras.

    Fornece métodos para criar, recuperar, atualizar e apaga categorias
    """

    @staticmethod
    def create(category_form, user):
        """
        Cria uma nova categoria no banco de dados.

        Parâmetros:
            category_form (CategoryForm): Formulário contendo os dados da categoria.
            user (User): Usuário que está criando a categoria.

        Retorna:
            Category: A categoria criada.
        """
        category = category_form.save(commit=False)
        category.user = user
        category.save()
        return category


    @staticmethod
    def get_categories(user):
        """ 
        Recupera todas as categorias de um usuário

        Parâmetros:
            user (User): Usuário que está recuperando a categoria.

        Retorna:
            Categories: Todas as categorias daquele usuário
        """
        return Category.objects.filter(user=user)


    @staticmethod
    def get_categories_by_type(type, user):
        """
        Recupera todas as categorias por tipo

        Parâmetros:
            type (str): entrada ou saida
            user (User): Usuário que está recuperando a categoria.

        Retorna:
            Categories: Todas as categorias daquele usuário
        """
        return Category.objects.filter(type=type, user=user)


    @staticmethod
    def get_category_by_id(id, user):
        """
        Recupera uma categoria por id

        Parâmetros:
            id (int): chave primária da categoria
            user (User): Usuário que está recuperando a categoria.

        Retorna:
            Categories: Todas as categorias daquele usuário
        """
        categoria = Category.objects.get(id=id, user=user)
        return categoria


    @staticmethod
    def update(category_form, category):
        """
        Atualiza uma categoria existente

        Parâmetros:
            category_form (CategoryForm): Formulário contendo os dados da categoria.
            category (Category): A categoria que está sendo editada

        Retorna:
            Category: A categoria atualizada.
        """
        updated_category = category_form.save(commit=False)
        model_fields = [field.name for field in Category._meta.fields if field.name != 'id']

        for field in model_fields:
            setattr(category, field, getattr(updated_category, field))
        category.save()
        return category


    @staticmethod
    def delete(category):
        """
        Apaga uma categoria existente

        Parâmetros:
            category (Category): A categoria que está sendo apagada
        """
        category.delete()
