from statement.models import Portion


def create_portion(portion):
    new_portion = Portion.objects.create(
        date=portion.date,
        value=portion.value,
        dream=portion.dream,
        user=portion.user
    )
    return new_portion


def list_portions(user):
    return Portion.objects.filter(user=user)


def list_portion_by_id(id, user):
    return Portion.objects.get(id=id, user=user)


def list_portions_by_dream(dream, user):
    return Portion.objects.filter(dream=dream, user=user)


def calculate_remaining_value(dream_id, dream_value, user):
    portions = list_portions_by_dream(dream_id, user)
    total_paid = sum(portion.value for portion in portions)
    remaining_value = dream_value - total_paid
    return remaining_value


def update_portion(old_portion, new_portion):
    old_portion.description=new_portion.description,
    old_portion.value=new_portion.value,
    old_portion.dream=new_portion.dream,
    old_portion.user=new_portion.user
    old_portion.save(force_update=True)


def delete_portion(portion):
    portion.delete()