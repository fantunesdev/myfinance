from statement.models import Subcategory


def create_subcategory(subcategory):
    new_subcategory = Subcategory.objects.create(
        description=subcategory.description,
        category=subcategory.category,
        user=subcategory.user,
    )
    return new_subcategory


def get_subcategories(user):
    return Subcategory.objects.filter(user=user)


def get_subcategory_by_id(id, user):
    return Subcategory.objects.get(id=id, user=user)


def update_subcategory(old_subcategory, new_subcategory):
    old_subcategory.description = new_subcategory.description
    old_subcategory.categoria = new_subcategory.category
    old_subcategory.save(force_update=True)
    return old_subcategory


def delete_subcategory(subcategory):
    subcategory.delete()
