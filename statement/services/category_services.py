from statement.models import Category


def create_category(category):
    new_category = Category.objects.create(
        type=category.type,
        description=category.description,
        color=category.color,
        icon=category.icon,
        ignore=category.ignore,
        user=category.user
    )
    return new_category


def get_categories(user):
    return Category.objects.filter(user=user)


def get_categories_by_type(type, user):
    return Category.objects.filter(type=type, user=user)


def get_category_by_id(id, user):
    categoria = Category.objects.get(id=id, user=user)
    return categoria


def update_category(old_category, new_category):
    old_category.type = new_category.type
    old_category.description = new_category.description
    old_category.color = new_category.color
    old_category.icon = new_category.icon
    old_category.ignore = new_category.ignore
    old_category.user = new_category.user
    old_category.save(force_update=True)


def delete_category(category):
    category.delete()
