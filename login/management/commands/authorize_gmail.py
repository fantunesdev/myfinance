"""Local, interactive OAuth authorization for the application's sender only."""
import json
import os
import secrets
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from django.core.management.base import BaseCommand, CommandError
from requests_oauthlib import OAuth2Session

CALLBACK_PATH = '/oauth/gmail/callback/'
SCOPE = 'https://www.googleapis.com/auth/gmail.send'


class Command(BaseCommand):
    requires_system_checks = []
    help = 'Autoriza o remetente Gmail localmente e grava o refresh token em arquivo com permissão 600.'

    def add_arguments(self, parser):
        parser.add_argument('--client-file', required=True, help='JSON do cliente OAuth Web baixado do Google.')
        parser.add_argument('--output', required=True, help='Novo arquivo JSON privado para guardar o refresh token.')
        parser.add_argument('--port', type=int, default=8766)

    def handle(self, *args, **options):
        target = Path(options['output']).expanduser().resolve()
        if target.exists():
            raise CommandError('O arquivo de saída já existe. Escolha um novo caminho para reautorizar.')
        try:
            client = json.loads(Path(options['client_file']).expanduser().read_text())['web']
            client_id, client_secret = client['client_id'], client['client_secret']
        except (OSError, ValueError, KeyError, TypeError):
            raise CommandError('Informe o JSON de um cliente OAuth do tipo Aplicativo da Web.') from None
        redirect_uri = f'http://localhost:{options["port"]}{CALLBACK_PATH}'
        if redirect_uri not in client.get('redirect_uris', []):
            raise CommandError(f'Cadastre {redirect_uri} no cliente Google e baixe novamente o JSON.')
        oauth = OAuth2Session(client_id, scope=[SCOPE], redirect_uri=redirect_uri)
        authorization_url, state = oauth.authorization_url(
            'https://accounts.google.com/o/oauth2/v2/auth',
            access_type='offline',
            prompt='consent',
        )
        result = {}

        class Callback(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass  # The callback URL contains a single-use authorization code.

            def do_GET(self):
                parsed = urlsplit(self.path)
                params = parse_qs(parsed.query)
                valid = parsed.path == CALLBACK_PATH and secrets.compare_digest(params.get('state', [''])[0], state)
                if not valid:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b'Autorizacao invalida. Volte ao terminal.')
                    return
                result['code'] = params.get('code', [''])[0]
                result['error'] = params.get('error', [''])[0]
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                self.wfile.write('Pode fechar esta janela e voltar ao terminal.'.encode())

        try:
            with HTTPServer(('127.0.0.1', options['port']), Callback) as server:
                server.timeout = 1
                self.stdout.write('Abra o endereço abaixo e escolha SOMENTE a conta remetente do MyFinance:')
                self.stdout.write(authorization_url)
                deadline = time.monotonic() + 300
                while not result and time.monotonic() < deadline:
                    server.handle_request()
            if not result.get('code') or result.get('error'):
                raise CommandError('Autorização cancelada ou expirada. Execute o comando novamente.')
            token = oauth.fetch_token(
                'https://oauth2.googleapis.com/token',
                code=result['code'],
                client_secret=client_secret,
                timeout=15,
            )
            refresh_token = token.get('refresh_token')
            if not refresh_token or SCOPE not in token.get('scope', []):
                raise CommandError('O Google não concedeu envio offline. Confira a permissão e autorize novamente.')
            descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, 'w') as output:
                json.dump({'refresh_token': refresh_token}, output)
        except CommandError:
            raise
        except Exception:
            raise CommandError(
                'Não foi possível concluir a autorização. Verifique o cliente, a conexão e o arquivo de saída.'
            ) from None
        self.stdout.write(self.style.SUCCESS(f'Autorização salva em {target}. Nenhum e-mail foi enviado.'))
