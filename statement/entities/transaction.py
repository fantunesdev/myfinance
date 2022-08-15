class Transaction:
    def __init__(self, release_date, payment_date, account, card, category, subcategory, description, value,
                 installments_number, paid, fixed, annual, currency, observation, remember, type, effected, home_screen,
                 user, installment):
        self.release_date = release_date
        self.payment_date = payment_date
        self.account = account
        self.card = card
        self.category = category
        self.subcategory = subcategory
        self.description = description
        self.value = value
        self.installments_number = installments_number
        self.paid = paid
        self.fixed = fixed
        self.annual = annual
        self.currency = currency
        self.observation = observation
        self.remember = remember
        self.type = type
        self.effected = effected
        self.home_screen = home_screen
        self.user = user
        self.installment = installment
