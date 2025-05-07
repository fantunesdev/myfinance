from django.db import models

from login.models import User


class Category(models.Model):
    """
    Classe que representa uma categoria de transação.

    Atributos:
        type (CharField): Tipo da categoria (entrada ou saída).
        description (CharField): Descrição da categoria.
        color (CharField): Cor da categoria.
        icon (CharField): Ícone da categoria.
        ignore (BooleanField): Se a categoria deve ser ignorada.
    """

    TYPE_CHOICES = (('entrada', 'Entrada'), ('saida', 'Saída'))
    type = models.CharField(max_length=7, choices=TYPE_CHOICES, default='saida')
    description = models.CharField(max_length=30)
    color = models.CharField(max_length=7, null=True, blank=True)
    icon = models.CharField(max_length=100, null=True, blank=True)
    ignore = models.BooleanField(blank=True)

    def __str__(self):
        """Retorna a descrição da categoria."""
        return self.description


class Subcategory(models.Model):
    """
    Classe que representa uma subcategoria de transação.

    Atributos:
        description (CharField): Descrição da subcategoria.
        category (ForeignKey): Categoria à qual a subcategoria pertence.
    """

    description = models.CharField(max_length=30)
    category = models.ForeignKey(Category, related_name='subcategories', on_delete=models.PROTECT)

    def __str__(self):
        """Retorna a descrição da subcategoria."""
        return self.description

    class Meta:
        """Ordena as subcategorias pela descrição."""

        ordering = ['description']


class CategorizationFeedback(models.Model):
    """
    Classe que salva o feedback categorizações feitas pelo Transaction Classifier.

    Atributos:
        user (User): Usuário que fez o feedback.
        description (CharField): Descrição da transação.
        predicted_category_id (ForeignKey): Categoria prevista pelo Transaction Classifier.
        predicted_subcategory_id (ForeignKey): Subcategoria prevista pelo Transaction Classifier.
        corrected_description (CharField): Descrição corrigida pelo usuário.
        corrected_category_id (ForeignKey): Categoria corrigida pelo usuário.
        corrected_subcategory_id (ForeignKey): Subcategoria corrigida pelo usuário.
        created_at (DateTimeField): Data e hora em que a categorização foi feita.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.CharField(max_length=255)
    predicted_category_id = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='+')
    predicted_subcategory_id = models.ForeignKey(Subcategory, on_delete=models.SET_NULL, null=True, related_name='+')
    corrected_description = models.CharField(max_length=255)
    corrected_category_id = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='+')
    corrected_subcategory_id = models.ForeignKey(Subcategory, on_delete=models.SET_NULL, null=True, related_name='+')
    subcategory_training = models.BooleanField(default=False)
    description_training = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class Bank(models.Model):
    """
    Classe que representa um banco.

    Atributos:
        description (CharField): Descrição do banco.
        code (CharField): Código do banco.
        icon (ImageField): Ícone do banco.
    """

    description = models.CharField(max_length=30)
    code = models.CharField(max_length=10, blank=True, null=True)
    icon = models.ImageField(upload_to='img/', null=True, blank=True)

    def __str__(self):
        """Retorna a descrição do banco."""
        return self.description


class AccountType(models.Model):
    """
    Classe que representa um tipo de conta.

    Atributos:
        description (CharField): Descrição do tipo de conta.
    """

    description = models.CharField(max_length=15)

    def __str__(self):
        """Retorna a descrição do tipo de conta."""
        return self.description


class Account(models.Model):
    """
    Classe que representa uma conta bancária.

    Atributos:
        bank (ForeignKey): Banco ao qual a conta pertence.
        branch (CharField): Agência da conta.
        number (CharField): Número da conta.
        balance (FloatField): Saldo da conta.
        limits (FloatField): Limite da conta.
        type (ForeignKey): Tipo da conta.
        home_screen (BooleanField): Se a conta deve aparecer na tela inicial.
        file_handler_conf (TextField): Configuração do manipulador de arquivos.
        user (ForeignKey): Usuário que possui a conta.
    """

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
        """Retorna a descrição da conta."""
        type = self.type.description
        first_letters = ''.join([word[0] for word in type.split()])
        return f'{self.bank.description} ({first_letters})'


class Flag(models.Model):
    """
    Classe que representa uma bandeira de cartão de crédito.

    Atributos:
        description (CharField): Descrição da bandeira.
        icon (ImageField): Ícone da bandeira.
    """

    description = models.CharField(max_length=20)
    icon = models.ImageField(upload_to='img/', null=True, blank=True)

    def __str__(self):
        """Retorna a descrição da bandeira do cartão."""
        return self.description


class Card(models.Model):
    """Classe que representa um cartão de crédito.
    Atributos:
        bank (ForeignKey): Banco ao qual o cartão pertence.
        number (CharField): Número do cartão.
        limit (FloatField): Limite do cartão.
        flag (ForeignKey): Bandeira do cartão.
        icon (ImageField): Ícone do cartão.
        description (CharField): Descrição do cartão.
        limits (FloatField): Limite do cartão.
        account (ForeignKey): Conta associada ao cartão.
        expiration_day (IntegerField): Dia de vencimento da fatura.
        closing_day (IntegerField): Dia de fechamento da fatura.
        home_screen (BooleanField): Se o cartão deve aparecer na tela inicial.
        file_handler_conf (TextField): Configuração do manipulador de arquivos.
        user (ForeignKey): Usuário que possui o cartão.
    """

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
        """Retorna a descrição do cartão de crédito."""
        return self.description


class Currency(models.Model):
    """
    Classe que representa uma moeda.

    Atributos:
        id (CharField): ID da moeda.
        description (CharField): Descrição da moeda.
        symbol (CharField): Símbolo da moeda.
    """

    id = models.CharField(max_length=3, primary_key=True)
    description = models.CharField(max_length=20)
    symbol = models.CharField(max_length=5)

    def __str__(self):
        """Retorna a descrição da moeda."""
        return self.description


class Installment(models.Model):
    """
    Classe que representa uma parcela de um pagamento.

    Atributos:
        release_date (DateField): Data de lançamento da parcela.
        description (CharField): Descrição da parcela.
        user (ForeignKey): Usuário que possui a parcela.
    """

    release_date = models.DateField()
    description = models.CharField(max_length=50)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        """Retorna a descrição da parcela."""
        return self.description


class Transaction(models.Model):
    """
    Classe que representa uma transação financeira.

    Atributos:
        release_date (DateField): Data de lançamento da transação.
        payment_date (DateField): Data de pagamento da transação.
        account (ForeignKey): Conta associada à transação.
        card (ForeignKey): Cartão associado à transação.
        category (ForeignKey): Categoria da transação.
        subcategory (ForeignKey): Subcategoria da transação.
        description (CharField): Descrição da transação.
        value (FloatField): Valor da transação.
        installments_number (IntegerField): Número de parcelas da transação.
        paid (IntegerField): Número de parcelas pagas.
        fixed (BooleanField): Se a transação é fixa.
        annual (BooleanField): Se a transação é anual.
        currency (ForeignKey): Moeda da transação.
        observation (TextField): Observação da transação.
        remember (BooleanField): Se a transação deve ser lembrada.
        type (CharField): Tipo da transação (entrada ou saída).
        effected (BooleanField): Se a transação foi efetivada.
        home_screen (BooleanField): Se a transação deve aparecer na tela inicial.
        user (ForeignKey): Usuário que possui a transação.
        installment (ForeignKey): Parcelamento associada à transação.
    """

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
        """Retorna a descrição da transação."""
        return self.description

    class Meta:
        """Ordena as transações pela data de lançamento."""

        ordering = ['release_date']


class NextMonthView(models.Model):
    day = models.IntegerField()
    active = models.BooleanField(blank=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT)


class FixedExpenses(models.Model):
    """
    Classe que representa uma despesa fixa.

    Atributos:
        start_date (DateField): Data de início da despesa.
        end_date (DateField): Data de fim da despesa.
        description (CharField): Descrição da despesa.
        value (FloatField): Valor da despesa.
        user (ForeignKey): Usuário que possui a despesa.
    """

    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    description = models.CharField(max_length=50)
    value = models.FloatField(default=0)
    user = models.ForeignKey(User, on_delete=models.PROTECT)

    def __str__(self):
        return self.description


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
    """Classe que representa um sonho.

    Atributos:
        description (CharField): Descrição do sonho.
        value (FloatField): Valor do sonho.
        limit_date (DateField): Data limite para realizar o sonho.
        user (ForeignKey): Usuário que possui o sonho.
    """

    description = models.CharField(max_length=70)
    value = models.FloatField()
    limit_date = models.DateField()
    user = models.ForeignKey(User, on_delete=models.PROTECT)


class Portion(models.Model):
    """
    Classe que representa uma parcela de um sonho.

    Atributos:
        date (DateField): Data da parcela.
        value (FloatField): Valor da parcela.
        dream (ForeignKey): Referência ao sonho associado.
        user (ForeignKey): Usuário que possui a parcela.
    """

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

    class Meta:
        ordering = ['investment_date']


class Ticker(models.Model):
    """
    Representa um ticker de ativo financeiro.
    Atributos:
        description (CharField): Descrição do ticker.
        code (CharField): Código do ticker.
    """

    description = models.CharField(max_length=255)
    code = models.CharField(max_length=10)

    def __str__(self):
        """Retorna a descrição do ticker."""
        return self.code

    class Meta:
        """Ordena os tickers pela descrição."""

        ordering = ['description']


class Sector(models.Model):
    """
    Representa um setor de mercado.
    Atributos:
        description (CharField): Descrição do setor.
    """

    description = models.CharField(max_length=255)

    def __str__(self):
        """Retorna a descrição do setor."""
        return self.description

    class Meta:
        """Ordena os setores pela descrição."""

        ordering = ['description']


class VariableIncome(models.Model):
    """
    Representa um ativo de renda variável.

    Atributos:
        account (ForeignKey): Conta associada ao ativo.
        ticker (ForeignKey): Ticker do ativo.
        user (ForeignKey): Usuário que possui o ativo.
    """

    CHOICES = [('active', 'Ativo'), ('sold', 'Vendido')]

    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    ticker = models.ForeignKey(Ticker, on_delete=models.PROTECT)
    user = models.ForeignKey(User, on_delete=models.PROTECT)

    def __str__(self):
        """Retorna o código do ticker associado ao ativo."""
        return self.ticker.code

    class Meta:
        """Ordena os ativos pela data de aquisição e pelo código do ticker."""

        ordering = ['ticker__code']


class AssetTransaction(models.Model):
    """
    Representa uma transação de ativo.

    Atributos:
        variable_income (ForeignKey): Ativo associado à transação.
        quantity (PositiveIntegerField): Quantidade de ativos transacionados.
        value (DecimalField): Valor da transação.
        transaction_type (CharField): Tipo da transação (compra ou venda).
        date (DateField): Data da transação.
        broker_fee (DecimalField): Taxa do corretor associada à transação.
        capital_gain_tax (DecimalField): Imposto sobre ganho de capital associado à transação.
    """

    CHOICES = [('buy', 'Compra'), ('sell', 'Venda')]

    variable_income = models.ForeignKey(VariableIncome, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    value = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=CHOICES)
    date = models.DateField()
    broker_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    capital_gain_tax = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        """Ordena as transações pela data."""

        ordering = ['date']
