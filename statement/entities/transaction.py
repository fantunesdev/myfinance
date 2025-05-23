import json

from statement.services.core.card import CardService


class Transaction:
    def __init__(
        self,
        release_date,
        payment_date,
        account,
        card,
        category,
        subcategory,
        description,
        value,
        installments_number,
        paid,
        fixed,
        annual,
        currency,
        observation,
        remember,
        type,
        effected,
        home_screen,
        user,
        installment,
    ):
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

    def __str__(self) -> str:
        return self.description

    def __repr__(self) -> str:
        return f"""
        Transaction:
            release_date: {self.release_date}
            payment_date: {self.payment_date}
            account: {self.account} 
            card: {self.card}
            category: {self.category}
            subcategory: {self.subcategory}
            description: {self.description}
            value: {self.value}
            installments_number: {self.installments_number}
            paid: {self.paid}
            fixed: {self.fixed}
            annual: {self.annual}
            currency: {self.currency}
            observation: {self.observation}
            remember: {self.remember}
            type: {self.type}
            effected: {self.effected}
            home_screen: {self.home_screen}
            user: {self.user}
            installment: {self.installment}
        """

    def to_dict(self):
        return self.__dict__

    def set_payment_date(self):
        if self.card:
            self.card = CardService.get_by_id(self.card)
            return
        return self.release_date
