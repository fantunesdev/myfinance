from statement.models import Flag


def create_flag(flag):
    new_flag = Flag.objects.create(
        description=flag.description,
        icon=flag.icon
    )
    return new_flag


def get_flags():
    return Flag.objects.all()


def get_flag_by_id(id):
    return Flag.objects.get(id=id)


def update_flag(old_flag, new_flag):
    old_flag.description = new_flag.description
    old_flag.icon = new_flag.icon
    old_flag.save(force_update=True)


def delete_flag(flag):
    flag.delete()
