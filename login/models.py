from django.contrib.auth.models import AbstractBaseUser
from django.db import models
from datetime import datetime
from login.manager import UsuarioManager

# Create your models here.


class Usuario(AbstractBaseUser):
    objects = UsuarioManager()
    nome = models.CharField(max_length=100, null=False, blank=False)
    email = models.EmailField(unique=True, null=False, blank=False)
    username = models.CharField(unique=True, max_length=50, null=False, blank=False)
    date_joined = models.DateTimeField(null=False, blank=False)
    foto = models.ImageField(upload_to='imagens/', null=True, blank=True)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['nome', 'email', 'date_joined']

    def __str__(self):
        return self.nome, self.email, self.username, self.password
