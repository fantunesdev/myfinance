from balanco.models import Antecipation


def create_antecipation(antecipation):
    antecipation_db = read_atecipation_user(antecipation.user)
    if antecipation_db:
        return antecipation_db
    else:
        new_antecipation = Antecipation.objects.create(
            day=antecipation.day,
            active=antecipation.antecipate,
            user=antecipation.user
        )
        return new_antecipation


def read_antecipation_id(id, user):
    return Antecipation.objects.get(id=id, user=user)


def read_atecipation_user(user):
    return Antecipation.objects.get(user=user)


def update_antecipation(old_antecipation, new_antecipation):
    old_antecipation.day = new_antecipation.day
    old_antecipation.active = new_antecipation.active
    old_antecipation.user = new_antecipation.user
    old_antecipation.save(force_update=True)


def delete_antecipation(antecipation):
    antecipation.delete()
