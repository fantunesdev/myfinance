class FixedExpense:
    def __init__(self, start_date, end_date, description, value, user):
        self.start_date = start_date
        self.end_date = end_date
        self.description = description
        self.value = value
        self.user = user

    def __str__(self) -> str:
        return self.description