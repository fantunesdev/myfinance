from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from login.models import User


class Broker(models.Model):
    KIND_CHOICES = (
        ('bank', 'Banco'),
        ('broker', 'Corretora'),
        ('exchange', 'Exchange'),
        ('wallet', 'Carteira'),
        ('other', 'Outro'),
    )

    description = models.CharField(max_length=80)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default='broker')
    user = models.ForeignKey(User, on_delete=models.PROTECT)

    def __str__(self):
        return self.description

    @property
    def kind_label(self):
        return self.get_kind_display()

    class Meta:
        ordering = ['description']
        unique_together = ('description', 'user')


class Asset(models.Model):
    TYPE_CHOICES = (
        ('fixed_income', 'Renda fixa'),
        ('variable_income', 'Renda variável'),
        ('crypto', 'Cripto'),
        ('currency', 'Moeda'),
        ('other', 'Outro'),
    )
    INCOME_BEHAVIOR_CHOICES = (
        ('none', 'Não gera renda'),
        ('interest', 'Juros/rendimento'),
        ('dividend', 'Dividendos/proventos'),
    )

    description = models.CharField(max_length=120)
    symbol = models.CharField(max_length=20, blank=True)
    asset_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    income_behavior = models.CharField(max_length=20, choices=INCOME_BEHAVIOR_CHOICES, default='none')
    currency = models.CharField(max_length=3, default='BRL')
    user = models.ForeignKey(User, on_delete=models.PROTECT)

    def __str__(self):
        return self.symbol or self.description

    @property
    def asset_type_label(self):
        return self.get_asset_type_display()

    @property
    def income_behavior_label(self):
        return self.get_income_behavior_display()

    class Meta:
        ordering = ['asset_type', 'description']
        unique_together = ('description', 'symbol', 'user')


class Investment(models.Model):
    hidden_detail_fields = ('default_wallet_for', 'default_wallet_for_id')
    STATUS_CHOICES = (
        ('active', 'Ativo'),
        ('closed', 'Encerrado'),
    )

    description = models.CharField(max_length=140)
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name='investments')
    broker = models.ForeignKey(Broker, on_delete=models.PROTECT, related_name='investments')
    start_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    notes = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    default_wallet_for = models.OneToOneField(
        User,
        null=True,
        blank=True,
        editable=False,
        on_delete=models.PROTECT,
        related_name='default_investment_wallet',
    )

    def __str__(self):
        return self.description

    @property
    def status_label(self):
        return self.get_status_display()

    class Meta:
        ordering = ['asset__asset_type', 'description']


class InvestmentTransaction(models.Model):
    hidden_detail_fields = (
        'operation_id',
        'funding_transaction',
        'funding_transaction_id',
        'redemption_principal',
    )
    TYPE_CHOICES = (
        ('aporte', 'Aporte/Aplicação'),
        ('resgate', 'Resgate'),
        ('rendimento', 'Rendimento/Provento'),
        ('atualizacao', 'Atualização de valor'),
        ('custo', 'Taxa/Imposto'),
    )

    investment = models.ForeignKey(Investment, on_delete=models.PROTECT, related_name='transactions')
    date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    quantity = models.DecimalField(
        max_digits=20, decimal_places=8, null=True, blank=True, validators=[MinValueValidator(Decimal('0.00000001'))]
    )
    unit_price = models.DecimalField(
        max_digits=14, decimal_places=6, null=True, blank=True, validators=[MinValueValidator(Decimal('0.000001'))]
    )
    current_value = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)]
    )
    statement_transaction = models.OneToOneField(
        'statement.Transaction',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='investment_transaction',
    )
    operation_id = models.UUIDField(null=True, blank=True, db_index=True)
    funding_transaction = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        editable=False,
        on_delete=models.PROTECT,
        related_name='funded_transactions',
    )
    redemption_principal = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        editable=False,
    )
    notes = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT)

    def __str__(self):
        return f'{self.get_type_display()} - {self.investment}'

    @property
    def type_label(self):
        return self.get_type_display()

    def clean(self):
        super().clean()
        if self.investment_id and self.user_id and self.investment.user_id != self.user_id:
            raise ValidationError('O investimento deve pertencer ao usuário da movimentação.')
        if self.type == 'atualizacao':
            if self.current_value is None:
                raise ValidationError({'current_value': 'Informe o valor atualizado.'})
        elif self.amount is None or self.amount <= 0:
            raise ValidationError({'amount': 'O valor deve ser maior que zero.'})

    class Meta:
        ordering = ['-date', '-id']
