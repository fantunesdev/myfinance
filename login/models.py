from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from login.manager import UserManager

# Create your models here.


class User(AbstractBaseUser, PermissionsMixin):
    """
    Classe do usuário
    """

    objects = UserManager()
    username = models.CharField(max_length=150, unique=True)
    name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    photo = models.ImageField(upload_to='img/', null=True, blank=True)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['name', 'email']

    def __str__(self):
        """Retorna o username do usuário"""
        return self.username

class Profile(models.Model):
    """
    Classe do perfil do usuário
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    use_next_month = models.BooleanField(default=False)
    next_month_day = models.PositiveSmallIntegerField(
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(31)],
    )
