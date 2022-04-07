from django.db import models

from login.models import Usuario


class Categoria(models.Model):
    TIPO_CHOICES = (
        ('entrada', 'Entrada'),
        ('saida', 'Saída')
    )
    tipo = models.CharField(max_length=7, choices=TIPO_CHOICES, default='saída')
    descricao = models.CharField(max_length=30)
    cor = models.CharField(max_length=7, null=True, blank=True)
    icone = models.CharField(max_length=100, null=True, blank=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT)

    def __str__(self):
        return self.descricao


class SubCategoria(models.Model):
    descricao = models.CharField(max_length=30)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT)

    def __str__(self):
        return self.descricao


class Banco(models.Model):
    descricao = models.CharField(max_length=30)
    codigo = models.CharField(max_length=10, blank=True, null=True)
    icone = models.ImageField(upload_to='imagens/', null=True, blank=True)

    def __str__(self):
        return self.descricao


class ContaTipo(models.Model):
    descricao = models.CharField(max_length=15,)

    def __str__(self):
        return self.descricao


class Conta(models.Model):
    banco = models.ForeignKey(Banco, on_delete=models.PROTECT)
    agencia = models.CharField(max_length=10, blank=True, null=True)
    numero = models.CharField(max_length=20, blank=True, null=True)
    saldo = models.FloatField(default=0,)
    limite = models.FloatField(default=0)
    tipo = models.ForeignKey(ContaTipo, on_delete=models.PROTECT)
    tela_inicial = models.BooleanField(default=False,)
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT)

    def __str__(self):
        return self.banco.descricao


class Bandeira(models.Model):
    descricao = models.CharField(max_length=20)
    icone = models.ImageField(upload_to='imagens/', null=True, blank=True)

    def __str__(self):
        return self.descricao


class Cartao(models.Model):
    bandeira = models.ForeignKey(Bandeira, on_delete=models.PROTECT)
    descricao = models.CharField(max_length=30)
    limite = models.FloatField(default=0)
    conta = models.ForeignKey(Conta, on_delete=models.PROTECT, null=True, blank=True)
    vencimento = models.IntegerField(blank=False, null=False)
    tela_inicial = models.BooleanField(default=False,)
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT)

    def __str__(self):
        return self.descricao


class Moeda(models.Model):
    id = models.CharField(max_length=3, primary_key=True)
    descricao = models.CharField(max_length=20)
    simbolo = models.CharField(max_length=5)

    def __str__(self):
        return self.descricao


class Movimentacao(models.Model):
    TIPO_CHOICES = (
        ('entrada', 'Entrada'),
        ('saida', 'Saída')
    )
    data_lancamento = models.DateField()
    data_efetivacao = models.DateField()
    conta = models.ForeignKey(Conta, on_delete=models.PROTECT, null=True, blank=True)
    cartao = models.ForeignKey(Cartao, on_delete=models.PROTECT, null=True, blank=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT)
    subcategoria = models.ForeignKey(SubCategoria, on_delete=models.PROTECT)
    descricao = models.CharField(max_length=50,)
    valor = models.FloatField(default=0)
    parcelas = models.IntegerField(default=0)
    pagas = models.IntegerField(default=0)
    fixa = models.BooleanField(default=False)
    anual = models.BooleanField(default=False)
    moeda = models.ForeignKey(Moeda, on_delete=models.PROTECT, default='BRL')
    observacao = models.TextField(blank=True, null=True)
    lembrar = models.BooleanField(default=False,)
    tipo = models.CharField(max_length=7, choices=TIPO_CHOICES, default='saida')
    efetivado = models.BooleanField(default=False)
    tela_inicial = models.BooleanField(default=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT)

    def __str__(self):
        return self.descricao
