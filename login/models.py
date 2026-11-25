import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from login.manager import UserManager


class PasswordResetDelivery(models.Model):
    """Short-lived outbox: tokens and recipient addresses are never persisted."""

    user = models.ForeignKey('login.User', null=True, on_delete=models.CASCADE)
    credential_fingerprint = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    available_at = models.DateTimeField(default=timezone.now, db_index=True)
    locked_until = models.DateTimeField(null=True)
    claim = models.UUIDField(null=True)
    attempts = models.PositiveSmallIntegerField(default=0)

# Create your models here.


class User(AbstractBaseUser, PermissionsMixin):
    """
    Classe do usuário
    """

    objects = UserManager()
    username = models.CharField(max_length=150, unique=True)
    name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    pending_email = models.EmailField(blank=True, default='', db_default='')
    email_confirmation_nonce = models.UUIDField(default=uuid.uuid4, null=True)
    email_requested_at = models.DateTimeField(null=True, blank=True)
    two_factor_enabled = models.BooleanField(default=False, db_default=False)
    security_version = models.PositiveIntegerField(default=0, db_default=0)
    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    photo = models.ImageField(upload_to='img/', null=True, blank=True)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['name', 'email']

    def _get_session_auth_hash(self, secret=None):
        if self.security_version == 0:
            return super()._get_session_auth_hash(secret=secret)
        from django.utils.crypto import salted_hmac
        return salted_hmac(
            'myfinance.security-session', f'{self.password}:{self.security_version}',
            secret=secret, algorithm='sha256',
        ).hexdigest()

    def __str__(self):
        """Retorna o username do usuário"""
        return self.username


class Profile(models.Model):
    """
    Classe do perfil do usuário
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    social_login_enabled = models.BooleanField(default=True)
    use_next_month = models.BooleanField(default=False)
    enable_fuel_tracking = models.BooleanField(default=False)
    inactivity_logout_enabled = models.BooleanField(default=False)
    inactivity_logout_minutes = models.PositiveSmallIntegerField(
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(1440)],
    )
    fuel_subcategory = models.ForeignKey(
        'statement.Subcategory',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    next_month_day = models.PositiveSmallIntegerField(
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(31)],
    )


class TwoFactorDevice(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    encrypted_secret = models.TextField(blank=True)
    pending_secret = models.TextField(blank=True)
    pending_created_at = models.DateTimeField(null=True)
    confirmed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_t = models.BigIntegerField(default=-1)
    failures = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True)


class RecoveryCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    digest = models.CharField(max_length=64)


class AccountEmailDelivery(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    kind = models.CharField(max_length=12)
    recipient = models.EmailField(blank=True)
    nonce = models.UUIDField(null=True)
    credential_stamp = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    available_at = models.DateTimeField(default=timezone.now, db_index=True)
    locked_until = models.DateTimeField(null=True)
    claim = models.UUIDField(null=True)
    attempts = models.PositiveSmallIntegerField(default=0)


class SecurityAuditEvent(models.Model):
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    kind = models.CharField(max_length=64)
    reason = models.CharField(max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
