from ..models import Bank


def create_bank(bank):
    Bank.objects.create(description=bank.description, code=bank.code, icon=bank.icon)


def get_banks():
    return Bank.objects.all()


def get_bank_by_id(id):
    return Bank.objects.get(id=id)


def update_bank(old_bank, new_bank):
    old_bank.description = new_bank.description
    old_bank.code = new_bank.code
    old_bank.icon = new_bank.icon
    old_bank.save(force_update=True)


def delete_bank(bank):
    bank.delete()
