class Account:
    def __init__(self, bank, branch, number, balance, limits, type, home_screen, user):
        self.bank = bank
        self.branch = branch
        self.number = number
        self.balance = balance
        self.limits = limits
        self.type = type
        self.home_screen = home_screen
        self.user = user

    def __str__(self) -> str:
        return f"""
        Account:
            bank: {self.bank}
            branch: {self.branch}
            number: {self.number}
            balance: {self.balance}
            limits: {self.limits}
            type: {self.type}
            home_screen: {self.home_screen}
            user: {self.user}
        """

