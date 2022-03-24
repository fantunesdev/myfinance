from django.db import models


class Categoria(models.Model):
    TIPO_CHOICES = (
        ('entrada', 'Entrada'),
        ('saida', 'Saída')
    )
    tipo = models.CharField(max_length=7, choices=TIPO_CHOICES, blank=False, null=False, default='saída')
    descricao = models.CharField(max_length=30, blank=False, null=False)
    cor = models.CharField(max_length=7, null=True, blank=True)
    icone = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.descricao


class Banco(models.Model):
    descricao = models.CharField(max_length=30, blank=False, null=False)
    codigo = models.CharField(max_length=10, blank=True, null=True)
    icone = models.ImageField(upload_to='imagens/', null=True, blank=True)

    def __str__(self):
        return self.descricao


class Conta(models.Model):
    banco = models.ForeignKey(Banco, on_delete=models.PROTECT)
    agencia = models.CharField(max_length=10, blank=True, null=True)
    numero = models.CharField(max_length=20, blank=True, null=True)
    saldo = models.FloatField(default=0, blank=False, null=False)
    limite = models.FloatField(default=0, blank=False, null=False)
    tela_inicial = models.BooleanField(default=False, blank=False, null=False)

    def __str__(self):
        return self.banco.descricao


class Bandeira(models.Model):
    descricao = models.CharField(max_length=20, blank=False, null=False)
    icone = models.ImageField(upload_to='imagens/', null=True, blank=True)


class Cartao(models.Model):
    descricao = models.CharField(max_length=30, blank=False, null=False)
    limite = models.FloatField(default=0, blank=False, null=False)
    bandeira = models.ForeignKey(Bandeira, on_delete=models.PROTECT)
    tela_inicial = models.BooleanField(default=False, blank=False, null=False)
    conta = models.ForeignKey(Conta, on_delete=models.PROTECT)
    fechamento = models.IntegerField(blank=False, null=False)
    pagamento = models.IntegerField(blank=True, null=True)


class Moeda(models.Model):
    id = models.CharField(max_length=3, primary_key=True, blank=False, null=False)
    descricao = models.CharField(max_length=20, blank=False, null=False)

    def __str__(self):
        return self.descricao


class Movimentacao(models.Model):
    valor = models.FloatField(default=0, blank=False, null=False)
    data = models.DateField()
    repetir = models.BooleanField(default=False, blank=False, null=False)
    parcelas = models.IntegerField(default=0, blank=True, null=True)
    descricao = models.CharField(max_length=50, blank=False, null=False)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT)
    conta = models.ForeignKey(Conta, on_delete=models.PROTECT)
    fixa = models.BooleanField(default=False, blank=False, null=False)
    moeda = models.ForeignKey(Moeda, on_delete=models.PROTECT, default='BRL')
    observacao = models.TextField(blank=True, null=True)
    lembrar = models.BooleanField(default=False, blank=False, null=False)
    tipo = models.BooleanField(blank=False, null=False)
    efetivado = models.BooleanField(default=False, blank=False, null=False)

    def __str__(self):
        return self.descricao
