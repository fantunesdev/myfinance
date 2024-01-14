from statement.models import Installment


def create_installment(installment):
    new_installment = Installment.objects.create(
        release_date=installment.release_date,
        description=installment.description,
        user=installment.user,
    )
    return new_installment


def get_installments(user):
    return Installment.objects.filter(user=user)


def get_installment_by_id(id, user):
    return Installment.objects.get(id=id, user=user)


def update_installment(old_installment, new_installment):
    old_installment.release_date = new_installment.release_date
    old_installment.description = new_installment.description
    old_installment.save(force_update=True)


def delete_installment(installment):
    installment.delete()
