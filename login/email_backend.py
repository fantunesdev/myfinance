"""Gmail API transport with refresh tokens kept outside the database and logs."""
import base64
import json
import time
from email.utils import parseaddr
from pathlib import Path

import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


class GmailDeliveryError(Exception):
    """Deliberately excludes provider payloads and authorization material."""


class GmailBackend(BaseEmailBackend):
    def __init__(self, fail_silently=False, *, timeout=15, **kwargs):
        super().__init__(**kwargs)
        self.fail_silently = fail_silently
        self.timeout = timeout
        self.access_token = None
        self.expires_at = 0

    def refresh(self):
        refresh_token = getattr(settings, 'GMAIL_REFRESH_TOKEN', '')
        token_file = getattr(settings, 'GMAIL_REFRESH_TOKEN_FILE', '')
        if token_file:
            refresh_token = json.loads(Path(token_file).read_text())['refresh_token']
        client_id = getattr(settings, 'GMAIL_CLIENT_ID', '')
        secret = getattr(settings, 'GMAIL_CLIENT_SECRET', '')
        if not all((client_id, secret, refresh_token)):
            raise GmailDeliveryError('Configure o cliente OAuth e o refresh token do remetente.')
        response = requests.post(
            'https://oauth2.googleapis.com/token',
            data={
                'client_id': client_id,
                'client_secret': secret,
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token',
            },
            timeout=(5, self.timeout),
        )
        response.raise_for_status()
        data = response.json()
        self.access_token = data['access_token']
        self.expires_at = time.monotonic() + max(0, int(data.get('expires_in', 3600)) - 60)

    def send_messages(self, email_messages):
        sent = 0
        for message in email_messages or []:
            if not message.recipients():
                continue
            try:
                # Gmail sends as the authorized mailbox (or an already configured alias).
                sender = getattr(settings, 'GMAIL_SENDER_EMAIL', '')
                if not sender or parseaddr(message.from_email)[1].casefold() != sender.casefold():
                    raise GmailDeliveryError('Configure o remetente autorizado do Gmail.')
                if not self.access_token or time.monotonic() >= self.expires_at:
                    self.refresh()
                mime = message.message()
                # Bcc recipients belong in the raw Gmail payload, but not in Django's normal MIME serialization.
                if message.bcc:
                    mime['Bcc'] = ', '.join(message.bcc)
                raw = base64.urlsafe_b64encode(mime.as_bytes()).decode('ascii')
                response = requests.post(
                    'https://gmail.googleapis.com/gmail/v1/users/me/messages/send',
                    headers={'Authorization': f'Bearer {self.access_token}'},
                    json={'raw': raw},
                    timeout=(5, self.timeout),
                )
                response.raise_for_status()
                if not response.json().get('id'):
                    raise GmailDeliveryError('O Gmail não confirmou o envio.')
                sent += 1
            except Exception:
                self.access_token = None
                self.expires_at = 0
                if not self.fail_silently:
                    raise GmailDeliveryError(
                        'Falha no envio pelo Gmail. Verifique a autorização da conta remetente.'
                    ) from None
        return sent
