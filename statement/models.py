from django.db import models

from login.models import User


class Category(models.Model):
    TYPE_CHOICES = (('entrada', 'Entrada'), ('saida', 'Saída'))
    type = models.CharField(max_length=7, choices=TYPE_CHOICES, default='saida')
    description = models.CharField(max_length=30)
    color = models.CharField(max_length=7, null=True, blank=True)
    icon = models.CharField(max_length=100, null=True, blank=True)
    ignore = models.BooleanField(blank=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT)

    def __str__(self):
        return self.description


class Subcategory(models.Model):
    description = models.CharField(max_length=30)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    user = models.ForeignKey(User, on_delete=models.PROTECT)

    def __str__(self):
        return self.description

    class Meta:
        ordering = ['description']


class Bank(models.Model):
    description = models.CharField(max_length=30)
    code = models.CharField(max_length=10, blank=True, null=True)
    icon = models.ImageField(upload_to='img/', null=True, blank=True)

    def __str__(self):
        return self.description


class AccountType(models.Model):
    description = models.CharField(max_length=15)

    def __str__(self):
        return self.description


class Account(models.Model):
    bank = models.ForeignKey(Bank, on_delete=models.PROTECT)
    branch = models.CharField(max_length=10, blank=True, null=True)
    number = models.CharField(max_length=20, blank=True, null=True)
    balance = models.FloatField(
        default=0,
    )
    limits = models.FloatField(default=0)
    type = models.ForeignKey(AccountType, on_delete=models.PROTECT)
    home_screen = models.BooleanField(
        default=False,
    )
    file_handler_conf = models.TextField(blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT)

    def __str__(self):
        return self.bank.description


class Flag(models.Model):
    description = models.CharField(max_length=20)
    icon = models.ImageField(upload_to='img/', null=True, blank=True)

    def __str__(self):
        return self.description


class Card(models.Model):
    flag = models.ForeignKey(Flag, on_delete=models.PROTECT)
    icon = models.ImageField(upload_to='img/', null=True, blank=True)
    description = models.CharField(max_length=30)
    limits = models.FloatField(default=0)
    account = models.ForeignKey(Account, on_delete=models.PROTECT, null=True, blank=True)
    expiration_day = models.IntegerField(blank=False, null=False)
    closing_day = models.IntegerField(blank=False, null=False)
    home_screen = models.BooleanField(default=False)
    file_handler_conf = models.TextField(blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT)

    def __str__(self):
        return self.description


class Currency(models.Model):
    id = models.CharField(max_length=3, primary_key=True)
    description = models.CharField(max_length=20)
    symbol = models.CharField(max_length=5)

    def __str__(self):
        return self.description


class Installment(models.Model):
    release_date = models.DateField()
    description = models.CharField(max_length=50)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.description


class Transaction(models.Model):
    TYPE_CHOICES = (('entrada', 'Entrada'), ('saida', 'Saída'))
    release_date = models.DateField()
    payment_date = models.DateField()
    account = models.ForeignKey(Account, on_delete=models.PROTECT, null=True, blank=True)
    card = models.ForeignKey(Card, on_delete=models.PROTECT, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    subcategory = models.ForeignKey(Subcategory, on_delete=models.PROTECT)
    description = models.CharField(max_length=255)
    value = models.FloatField(default=0)
    installments_number = models.IntegerField(default=0)
    paid = models.IntegerField(default=0)
    fixed = models.BooleanField(default=False)
    annual = models.BooleanField(default=False)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, default='BRL')
    observation = models.TextField(blank=True, null=True)
    remember = models.BooleanField(default=False)
    type = models.CharField(max_length=7, choices=TYPE_CHOICES, default='saida')
    effected = models.BooleanField(default=False)
    home_screen = models.BooleanField(default=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    installment = models.ForeignKey(Installment, null=True, blank=True, on_delete=models.CASCADE)

    def __str__(self):
        return self.description


class NextMonthView(models.Model):
    day = models.IntegerField()
    active = models.BooleanField(blank=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT)


class FixedExpenses(models.Model):
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    description = models.CharField(max_length=50)
    value = models.FloatField(default=0)
    user = models.ForeignKey(User, on_delete=models.PROTECT)


class Version(models.Model):
    """
    Versão do programa.

    Atributos:
        version (CharField): A versão do programa. Ex.: v1.0.31.
        date (DateField): o dia do release da versão.
    """
    version = models.CharField(max_length=30)
    date = models.DateField()


class Dream(models.Model):
    description = models.CharField(max_length=70)
    value = models.FloatField()
    limit_date = models.DateField()
    user = models.ForeignKey(User, on_delete=models.PROTECT)


class Portion(models.Model):
    date = models.DateField()
    value = models.FloatField()
    dream = models.ForeignKey(Dream, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.PROTECT)


class Index(models.Model):
    """
    Indice financeiro utilizado para cálculos de rendimento.

    Atributos:
        description (CharField): Nome do índice financeiro (ex: CDI, SELIC).
        bcb_id (Integer): ID do índice na API do Banco Central do Brasil
        first_date (Date): Data do primeiro registro do índice
    """

    description = models.CharField(max_length=100)
    bcb_id = models.IntegerField(null=True, blank=True)
    first_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.description

class IndexHistoricalSeries(models.Model):
    """
    Série histórica um índice financeiro utilizado para cálculos de rendimento.

    Atributos:
        index (CharField): Nome do índice financeiro (ex: CDI, SELIC).
        date (DateField): Data do índice.
        rate (FloatField): Valor da taxa do índice na data especificada, geralmente expresso em percentual.
    """

    index = models.ForeignKey(Index, on_delete=models.PROTECT)
    date = models.DateField()
    rate = models.FloatField()

    def __str__(self):
        return self.index.description


class FixedIncomeSecurity(models.Model):
    """
    Instrumento ou tipo de investimento.
    
    Exemplo:
        CDB - Crédito de Depósito Bancário
        LCI - Letra de Crédito Imobiliário

    Atributos:
        description {CharField} - Nome completo do instrumento
        abbreviation {CharField} - Abreviação do nome do instrumento
    """
    description = models.CharField(max_length=255)
    abbreviation = models.CharField(max_length=10)

    def __str__(self):
        return self.abbreviation


class FixedIncome(models.Model):
    """
    Um tipo de ativo de renda fixa no sistema financeiro.

    Atributos:
        account (Account): Referência ao modelo 'Account', representando a conta associada ao investimento.
        principal (FloatField): Valor principal investido.
        security {FloateField}: O instrumento ou tipo de investimento (Ex: CDB, LCI, Tesouro Direto, etc)
        investment_date (DateField): Data em que o investimento foi realizado.
        maturity_date (DateField): Data de vencimento do investimento.
        index: (Index) Referência ao modelo 'Index', representando o índice ao qual a taxa está vinculada (ex: CDI).
        contractual_rate (FloatField): Taxa contratada do investimento, expressa como uma porcentagem.
        user (User): Referência ao modelo 'User', indicando o usuário que fez o investimento.
    """

    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    principal = models.FloatField()
    security = models.ForeignKey(FixedIncomeSecurity, on_delete=models.PROTECT)
    investment_date = models.DateField()
    maturity_date = models.DateField()
    index = models.ForeignKey(Index, on_delete=models.PROTECT)
    contractual_rate = models.FloatField()
    user = models.ForeignKey(User, on_delete=models.PROTECT)
