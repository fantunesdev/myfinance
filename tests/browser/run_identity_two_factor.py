"""Real-browser identity and MFA workflow with isolated SQLite and in-memory email."""
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.request import urlopen
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def database_call(function):
    def run():
        from django.db import connections

        try:
            return function()
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(run).result()


def main():
    from cryptography.fernet import Fernet
    from playwright.sync_api import sync_playwright

    with tempfile.TemporaryDirectory(prefix='myfinance-identity-browser-') as directory:
        root = Path(directory)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        base = f'http://127.0.0.1:{port}'
        module = root / 'identity_browser_settings.py'
        module.write_text(
            'from myfinance.security_test_settings import *\n'
            "DEBUG=True\nSECRET_KEY='identity-browser-tests-only-'+ 'x'*40\n"
            f'TWO_FACTOR_ENCRYPTION_KEY={Fernet.generate_key().decode()!r}\nPUBLIC_BASE_URL={base!r}\n'
            "EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'\nDEFAULT_FROM_EMAIL='sender@browser.invalid'\n"
            "INSTALLED_APPS=['login.admin_apps.SecurityAdminConfig' if name=='django.contrib.admin' else name for name in INSTALLED_APPS]\n"
            "MIDDLEWARE.insert(MIDDLEWARE.index('django.contrib.auth.middleware.AuthenticationMiddleware')+1,'login.middleware.TwoFactorSessionMiddleware')\n"
            "REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'][0]='login.authentication.SecureSessionAuthentication'\n"
        )
        sys.path.insert(0, directory)
        os.environ['PYTHONPATH'] = directory + os.pathsep + str(ROOT)
        os.environ['MYFINANCE_E2E_DIRECTORY'] = directory
        os.environ['DJANGO_SETTINGS_MODULE'] = 'identity_browser_settings'
        import django

        django.setup()
        from django.core.management import call_command
        from django.core import mail
        from django_otp.oath import TOTP
        from login.models import User, TwoFactorDevice, RecoveryCode, AccountEmailDelivery
        from login.account_email import process_account_email
        from login import security
        from social_django.models import UserSocialAuth

        call_command('migrate', interactive=False, verbosity=0, skip_checks=True)
        user = User.objects.create_user(
            username='identity-browser',
            name='Identity browser',
            email='old@browser.invalid',
            password='LocalPassword!123',
            is_staff=True,
        )
        UserSocialAuth.objects.create(
            user=user,
            provider='google-oauth2',
            uid='synthetic-google',
            id_key='sub',
            extra_data={'email': 'google@browser.invalid', 'email_verified': True},
        )
        with (root / 'server.log').open('w') as log:
            server = subprocess.Popen(
                [sys.executable, 'manage.py', 'runserver', f'127.0.0.1:{port}', '--noreload', '--insecure'],
                cwd=ROOT,
                stdout=log,
                stderr=log,
            )
            try:
                for _ in range(100):
                    try:
                        urlopen(base + '/login/', timeout=1).close()
                        break
                    except OSError:
                        if server.poll() is not None:
                            raise RuntimeError('Browser server failed: ' + (root / 'server.log').read_text()[-1500:])
                        time.sleep(0.1)
                else:
                    raise RuntimeError('Browser server did not start.')
                with sync_playwright() as p:
                    browser = p.chromium.launch(
                        headless=True, executable_path=os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH')
                    )
                    try:
                        context = browser.new_context(viewport={'width': 1200, 'height': 900})
                        context.route(
                            '**/*',
                            lambda route: route.continue_()
                            if route.request.url.startswith(base + '/') or route.request.url.startswith('data:')
                            else route.abort(),
                        )
                        page = context.new_page()
                        page.goto(base + '/login/?next=/usuarios/seguranca/')
                        page.locator('input[name=username]').fill(user.username)
                        page.locator('input[name=password]').fill('LocalPassword!123')
                        page.get_by_role('button', name='Logar', exact=True).click()
                        page.wait_for_url('**/usuarios/seguranca/')
                        page.get_by_role('link', name='Usar este e-mail do Google', exact=False).click()
                        assert page.locator('#id_email').input_value() == 'google@browser.invalid'
                        with page.expect_response(lambda r: r.request.method == 'POST') as response:
                            page.get_by_role('button', name='Confirmar', exact=True).click()
                        assert response.value.status == 302 and response.value.request.headers.get('origin') == base
                        assert database_call(lambda: User.objects.get(pk=user.pk).email) == 'old@browser.invalid'
                        assert database_call(process_account_email)
                        link = re.search(re.escape(base) + r'([^\s]+)', mail.outbox[0].body).group(1)
                        page.goto(base + link)
                        with page.expect_response(lambda r: r.request.method == 'POST') as response:
                            page.get_by_role('button', name='Confirmar endereço', exact=True).click()
                        assert response.value.status == 302 and response.value.request.headers.get('origin') == base
                        page.wait_for_url('**/usuarios/seguranca/')
                        assert database_call(lambda: User.objects.get(pk=user.pk).email) == 'google@browser.invalid'
                        page.get_by_role('link', name='Configurar autenticador', exact=True).click()
                        page.get_by_role('button', name='Gerar QR Code', exact=True).click()
                        page.locator('#id_code').wait_for()
                        assert page.locator('img[alt="QR Code para configurar o autenticador"]').count() == 1
                        secret = database_call(
                            lambda: security.secret_for(TwoFactorDevice.objects.get(user=user), enrollment=True)
                        )
                        page.locator('#id_code').fill(f'{TOTP(secret).token():06d}')
                        page.get_by_role('button', name='Confirmar e ativar', exact=True).click()
                        page.get_by_role('heading', name='Guarde seus códigos de recuperação').wait_for()
                        codes = page.locator('li code').all_text_contents()
                        assert len(codes) == 10
                        page.goto(base + '/logout/')
                        page.goto(base + '/login/?next=/usuarios/seguranca/')
                        page.locator('input[name=username]').fill(user.username)
                        page.locator('input[name=password]').fill('LocalPassword!123')
                        page.get_by_role('button', name='Logar', exact=True).click()
                        page.wait_for_url('**/2fa/confirmar/')
                        assert context.request.get(base + '/admin/', max_redirects=0).status == 302
                        assert context.request.get(base + '/usuarios/seguranca/', max_redirects=0).status == 302
                        page.locator('#id_code').fill(codes[0])
                        page.get_by_role('button', name='Confirmar', exact=True).click()
                        page.wait_for_url('**/usuarios/seguranca/')
                        assert database_call(lambda: RecoveryCode.objects.filter(user=user).count()) == 9
                        assert context.request.get(base + '/admin/', max_redirects=0).status == 200
                        page.screenshot(path='/tmp/myfinance-identity-security.png', full_page=True)
                        print(
                            'Browser: Google email selection, mailbox confirmation, encrypted TOTP enrollment, backup codes, pre-OTP access rejection and Admin access passed. No real email sent.'
                        )
                    finally:
                        browser.close()
            finally:
                server.terminate()
                server.wait(timeout=10)


if __name__ == '__main__':
    main()
