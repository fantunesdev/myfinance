from django.contrib.auth.models import AbstractBaseUser
from django.db import models

from login.manager import *

# Create your models here.


class User(AbstractBaseUser):
    objects = UserManager()
    username = models.CharField(max_length=150, unique=True)
    name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    is_superuser = models.BooleanField()
    is_staff = models.BooleanField()
    is_active = models.BooleanField()
    date_joined = models.DateTimeField()
    photo = models.ImageField(upload_to='img/', null=True, blank=True)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['name', 'email']

    def __str__(self):
        return self.username
