from django.conf import settings
from django.core.checks import Error, Warning, register


@register()
def password_recovery_configuration(app_configs, **kwargs):
    from login.password_reset import public_origin

    issues = []
    try:
        public_origin()
    except Exception:
        issues.append(Warning('Configure PUBLIC_BASE_URL para gerar links de recuperação.', id='login.W001'))
    if getattr(settings, 'EMAIL_BACKEND', '') == 'login.email_backend.GmailBackend':
        required = ('GMAIL_CLIENT_ID', 'GMAIL_CLIENT_SECRET', 'GMAIL_SENDER_EMAIL')
        if not all(getattr(settings, name, '') for name in required) or not (
            getattr(settings, 'GMAIL_REFRESH_TOKEN', '') or getattr(settings, 'GMAIL_REFRESH_TOKEN_FILE', '')
        ):
            issues.append(
                Warning('Envio Gmail incompleto: configure cliente, remetente e refresh token.', id='login.W002')
            )
    for name in (
        'PASSWORD_RESET_TIMEOUT',
        'PASSWORD_RESET_RATE_WINDOW',
        'PASSWORD_RESET_IP_LIMIT',
        'PASSWORD_RESET_EMAIL_LIMIT',
    ):
        if getattr(settings, name, 1) <= 0:
            issues.append(Error(f'{name} precisa ser positivo.', id='login.E001'))
    if not 0 < (getattr(settings, 'EMAIL_TIMEOUT', None) or 15) <= 30:
        issues.append(Error('EMAIL_TIMEOUT precisa estar entre 1 e 30 segundos.', id='login.E002'))
    return issues
