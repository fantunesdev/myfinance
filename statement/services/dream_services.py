from statement.models import Dream


def create_dream(dream):
    new_dream = Dream.objects.create(
        description=dream.description,
        value=dream.value,
        limit_date=dream.limit_date,
        user=dream.user,
    )
    return new_dream


def list_dreams(user):
    return Dream.objects.filter(user=user)


def list_dream_by_id(id, user):
    return Dream.objects.get(id=id, user=user)


def update_dream(old_dream, new_dream):
    old_dream.description = new_dream.description
    old_dream.value = new_dream.value
    old_dream.limit_date = new_dream.limit_date
    old_dream.user = new_dream.user
    old_dream.save(force_update=True)


def delete_dream(dream):
    dream.delete()
