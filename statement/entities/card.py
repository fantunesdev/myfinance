class Card:
    def __init__(
        self,
        flag,
        icon,
        description,
        limits,
        account,
        expiration_day,
        closing_day,
        home_screen,
        user,
    ):
        self.flag = flag
        self.icon = icon
        self.description = description
        self.limits = limits
        self.account = account
        self.expiration_day = expiration_day
        self.closing_day = closing_day
        self.home_screen = home_screen
        self.user = user

    def __str__(self) -> str:
        return self.description
