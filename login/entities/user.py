class User:
    def __init__(
        self,
        username,
        password,
        name,
        email,
        is_superuser,
        is_staff,
        is_active,
        date_joined,
        photo,
    ):
        self.username = username
        self.password = password
        self.name = name
        self.email = email
        self.is_superuser = is_superuser
        self.is_staff = is_staff
        self.is_active = is_active
        self.date_joined = date_joined
        self.photo = photo
