class NextMonthView:
    def __init__(self, day, active, user):
        self.day = day
        self.active = active
        self.user = user

    def __str__(self) -> str:
        return self.active
