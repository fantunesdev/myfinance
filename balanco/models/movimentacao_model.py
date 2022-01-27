from django.db import models


class Categoria(models.Model):
    TIPO_CHOICES = (
        ('entrada', 'Entrada'),
        ('saida', 'Saída')
    )
    tipo = models.CharField(max_length=7, choices=TIPO_CHOICES, blank=False, null=False, default='saída')
    descricao = models.CharField(max_length=30, blank=False, null=False)
    cor = models.CharField(max_length=7, null=True, blank=True)
    icone = models.ImageField(upload_to='imagens/', null=True, blank=True)

    def __str__(self):
        return self.descricao