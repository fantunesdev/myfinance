"""Exercise native browser form submissions, Origin and CSRF using disposable data.

Run with .venv/bin/python tests/browser/run_password_recovery.py.
Optionally set PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH to an installed browser.
"""
import os
import socket
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def database_call(callback):
    # Playwright runs an event loop on this thread; keep synchronous ORM work outside it.
    from django.db import connections

    def run():
        try:
            return callback()
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(run).result()


def main():
    from playwright.sync_api import sync_playwright

    with tempfile.TemporaryDirectory(prefix='myfinance-recovery-browser-') as directory:
        os.environ['MYFINANCE_E2E_DIRECTORY'] = directory
        os.environ['DJANGO_SETTINGS_MODULE'] = 'myfinance.security_test_settings'
        import django
        django.setup()
        from django.contrib.auth.tokens import default_token_generator
        from django.core.management import call_command
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode
        from login.models import PasswordResetDelivery, User

        call_command('migrate', verbosity=0, interactive=False, skip_checks=True)
        user = User.objects.create_user(username='recovery-browser', name='Recovery browser',
                                        email='recovery@browser.invalid', password='OldSecret!123')
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        base = f'http://127.0.0.1:{port}'
        with (Path(directory) / 'server.log').open('w') as log:
            server = subprocess.Popen([sys.executable, 'manage.py', 'runserver', f'127.0.0.1:{port}',
                                       '--noreload', '--insecure'], cwd=ROOT, stdout=log, stderr=log)
            try:
                for _ in range(100):
                    try:
                        urlopen(base + '/login/', timeout=1).close()
                        break
                    except OSError:
                        if server.poll() is not None:
                            raise RuntimeError('Isolated browser server failed to start.')
                        time.sleep(0.1)
                else:
                    raise RuntimeError('Isolated browser server did not become ready.')
                with sync_playwright() as playwright:
                    executable = os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH')
                    browser = playwright.chromium.launch(headless=True, executable_path=executable)
                    try:
                        context = browser.new_context()
                        context.route('**/*', lambda route: route.continue_() if route.request.url.startswith(base + '/') else route.abort())
                        page = context.new_page()
                        request_url = base + '/usuarios/senha/recuperar/'

                        # Negative control: reproduce the original browser-only bug.
                        def old_header(route):
                            if route.request.method != 'GET':
                                return route.continue_()
                            response = route.fetch()
                            headers = dict(response.headers)
                            headers['referrer-policy'] = 'no-referrer'
                            route.fulfill(response=response, headers=headers)
                        page.route(request_url, old_header)
                        page.goto(request_url)
                        page.locator('#id_email').fill(user.email)
                        with page.expect_response(lambda response: response.request.method == 'POST') as failed:
                            page.get_by_role('button', name='Enviar instruções').click()
                        assert failed.value.status == 403
                        assert failed.value.request.headers.get('origin') == 'null'
                        assert not database_call(lambda: PasswordResetDelivery.objects.exists())
                        page.unroute(request_url, old_header)

                        # Corrected response: the real browser must send a non-null Origin.
                        page.goto(request_url)
                        page.locator('#id_email').fill(user.email)
                        with page.expect_response(lambda response: response.request.method == 'POST') as accepted:
                            page.get_by_role('button', name='Enviar instruções').click()
                        assert accepted.value.status == 302
                        assert accepted.value.request.headers.get('origin') == base
                        page.wait_for_url('**/recuperar/enviado/')
                        assert database_call(lambda: PasswordResetDelivery.objects.filter(user=user).exists())

                        token = default_token_generator.make_token(user)
                        uid = urlsafe_base64_encode(force_bytes(user.pk))
                        page.goto(base + f'/usuarios/senha/recuperar/{uid}/{token}/')
                        page.wait_for_url('**/set-password/')
                        page.locator('#id_new_password1').fill('NewSecret!Password123')
                        page.locator('#id_new_password2').fill('NewSecret!Password123')
                        with page.expect_response(lambda response: response.request.method == 'POST') as reset:
                            page.get_by_role('button', name='Salvar nova senha').click()
                        assert reset.value.status == 302
                        assert reset.value.request.headers.get('origin') == base
                        page.wait_for_url('**/recuperar/concluido/')
                        assert database_call(lambda: User.objects.get(pk=user.pk).check_password('NewSecret!Password123'))
                        assert not database_call(lambda: PasswordResetDelivery.objects.exists())
                        print('Browser: reproduced Origin null/403; request and reset succeed with strict-origin and CSRF enabled.')
                    finally:
                        browser.close()
            finally:
                server.terminate()
                server.wait(timeout=10)


if __name__ == '__main__':
    main()
