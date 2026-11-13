"""Exercise inactivity logout with Chromium and disposable data.

PLAYWRIGHT_BROWSERS_PATH=/tmp/myfinance-playwright .venv/bin/python tests/browser/run_inactivity_logout.py
"""
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def seed():
    import django
    django.setup()
    from django.core.management import call_command
    from django.test import Client
    from login.models import Profile, User

    call_command('migrate', verbosity=0)
    call_command('check', verbosity=0)
    user = User.objects.create_user(
        username='idle-browser', name='Idle browser', email='idle@browser.invalid', password='Browser!valid-7P-oak',
    )
    Profile.objects.create(user=user)
    sessions = []
    for _ in range(2):
        client = Client()
        client.force_login(user)
        sessions.append(client.cookies['sessionid'].value)
    return sessions


def run_browser(base, sessions, output):
    from playwright.sync_api import sync_playwright, expect

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)

        def context(session):
            ctx = browser.new_context(base_url=base, timezone_id='America/Sao_Paulo')
            ctx.add_cookies([{'name': 'sessionid', 'value': session, 'url': base}])
            ctx.route('**/*', lambda route: route.continue_() if route.request.url.startswith(base) else route.abort())
            return ctx

        ctx = context(sessions[0])
        a = ctx.new_page()
        a.clock.install()
        errors = []
        a.on('pageerror', lambda error: errors.append(str(error)))
        a.goto('/usuarios/perfil/')
        expect(a.get_by_text('Desativado.', exact=False)).to_be_visible()
        a.get_by_role('link', name='Editar privacidade e segurança').click()
        a.get_by_label('Sair automaticamente por inatividade').check()
        a.get_by_label('Tempo de inatividade em minutos').fill('1')
        a.get_by_role('button', name='Salvar').click()
        expect(a.get_by_text('Ativado — após 1 minuto(s)', exact=False)).to_be_visible()
        a.screenshot(path=str(output / 'profile.png'), full_page=True)
        b = ctx.new_page()
        b.goto('/usuarios/perfil/')
        # A browser in another session must remain authenticated after this one expires.
        independent = context(sessions[1])
        c = independent.new_page()
        c.clock.install()
        c.goto('/usuarios/perfil/')

        a.evaluate("""() => {
            const config = JSON.parse(document.getElementById('inactivity-logout-config').textContent);
            localStorage.setItem(`myfinance:inactivity:${config.session}:activity`, JSON.stringify(Date.now() - 50000));
        }""")
        b.get_by_role('heading', name='Privacidade e segurança').click()
        assert a.evaluate("""() => {
            const config = JSON.parse(document.getElementById('inactivity-logout-config').textContent);
            return Date.now() - JSON.parse(localStorage.getItem(`myfinance:inactivity:${config.session}:activity`)) < 5000;
        }""")
        print('PASS: atividade real em uma aba renova o prazo compartilhado', flush=True)

        # Simulate a suspended browser returning past the deadline, without waiting a minute.
        a.clock.fast_forward(61000)
        a.wait_for_url('**/login/?inactive=1')
        b.wait_for_url('**/login/?inactive=1')
        expect(a.get_by_role('status')).to_contain_text('Você saiu por inatividade')
        c.reload()
        expect(c.get_by_role('heading', name='Privacidade e segurança')).to_be_visible()
        print('PASS: logout por POST nas duas abas preserva a sessão de outro navegador', flush=True)
        a.go_back()
        a.wait_for_url('**/login/**')
        assert a.locator('.box-title', has_text='Privacidade e segurança').count() == 0
        print('PASS: botão Voltar não reexibe o perfil após o logout', flush=True)

        independent.set_offline(True)
        c.clock.fast_forward(61000)
        expect(c.locator('#inactivity-screen')).to_be_visible()
        expect(c.locator('main')).to_be_hidden()
        independent.set_offline(False)
        c.wait_for_url('**/login/?inactive=1')
        print('PASS: offline oculta os dados e a reconexão conclui o logout', flush=True)
        assert not errors, errors
        browser.close()


def main():
    output = Path('/tmp/myfinance-inactivity-browser-results')
    output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='myfinance-inactivity-') as temporary:
        os.environ['MYFINANCE_E2E_DIRECTORY'] = temporary
        os.environ['DJANGO_SETTINGS_MODULE'] = 'myfinance.security_test_settings'
        sessions = seed()
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            port = listener.getsockname()[1]
        base = f'http://127.0.0.1:{port}'
        with (output / 'server.log').open('w') as log:
            server = subprocess.Popen(
                [sys.executable, 'manage.py', 'runserver', f'127.0.0.1:{port}', '--noreload', '--insecure'],
                cwd=ROOT, env=os.environ.copy(), stdout=log, stderr=log,
            )
            try:
                for _ in range(100):
                    try:
                        urlopen(base + '/login/', timeout=1).close()
                        break
                    except OSError:
                        time.sleep(0.1)
                run_browser(base, sessions, output)
            finally:
                server.terminate()
                server.wait(timeout=10)


if __name__ == '__main__':
    main()
