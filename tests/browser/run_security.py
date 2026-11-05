"""Run the real application and Chromium against disposable, synthetic data.

    .venv/bin/python tests/browser/run_security.py

Requires the dev dependency playwright and `python -m playwright install chromium`.
The application database, uploads and server logs live only in a temporary directory.
Screenshots and results are retained in /tmp/myfinance-security-browser-results.
"""
import json
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
    if django.VERSION[:3] < (5, 2, 19):
        raise RuntimeError('Instale as dependências atualizadas do poetry.lock antes dos testes de tela.')
    django.setup()
    from django.core.management import call_command
    from django.utils import timezone
    from login.models import Profile, User
    from statement.models import (Account, AccountType, AppConfig, Bank, Card, CardNumber,
                                  Category, Currency, Device, Flag, Installment, Notification,
                                  NotificationTitle, NotificationTitlePreference,
                                  Subcategory, Transaction, Version)
    call_command('migrate', verbosity=0)
    call_command('check', verbosity=0)
    users = [User.objects.create_user(username=name, name=name, email=f'{name}@browser.invalid',
                                      password='Browser!valid-7P-oak', is_staff=name == 'staff')
             for name in ('owner', 'other', 'staff', 'disabled')]
    for user in users:
        Profile.objects.create(user=user)
    users[3].is_active = False
    users[3].save(update_fields=['is_active'])
    device = Device.objects.create(user=users[3], name='Synthetic device')
    bank = Bank.objects.create(description='Browser Bank', app_id='br.com.intermedium')
    kind = AccountType.objects.create(description='Account')
    accounts = [Account.objects.create(user=user, bank=bank, type=kind, number=f'PRIVATE-ACCOUNT-{user.pk}', home_screen=True)
                for user in users[:2]]
    flag = Flag.objects.create(description='Browser Flag')
    cards = [Card.objects.create(user=user, account=accounts[index], flag=flag,
                                description=f'Card {user.pk}', closing_day=3, expiration_day=10)
             for index, user in enumerate(users[:2])]
    payload = '</script><img src=x onerror=window.__xss=1>'
    numbers = [CardNumber.objects.create(card=card, number=f'000{card.pk}',
                                        name=payload if index == 0 else 'PRIVATE-FOREIGN-CARD')
               for index, card in enumerate(cards)]
    category = Category.objects.create(description='Browser category', type='saida')
    subcategory = Subcategory.objects.create(description='Browser subcategory', category=category)
    Currency.objects.get_or_create(pk='BRL', defaults={'description': 'Real', 'symbol': 'R$'})
    today = timezone.localdate()
    plan = Installment.objects.create(user=users[1], description='PRIVATE-PLAN', posted_date=today)
    Transaction.objects.create(user=users[1], installment=plan, category=category, subcategory=subcategory,
        description='PRIVATE-PLAN-TRANSACTION', value=50, posted_date=today, payment_date=today)
    own_transaction = Transaction.objects.create(user=users[0], account=accounts[0], category=category,
        subcategory=subcategory, description='<img src=x onerror=window.__xss=2>', value=10,
        posted_date=today, payment_date=today, home_screen=True)
    # Legacy invalid FK must not leak through expansion even after write validation is fixed.
    legacy = Transaction.objects.create(user=users[0], account=accounts[1], category=category,
        subcategory=subcategory, description='Legacy relation', value=1, posted_date=today, payment_date=today)
    notification = Notification.objects.create(user=users[1], app='bank', title='Private', message='PRIVATE-MESSAGE')
    own_notification = Notification.objects.create(user=users[0], card=cards[0], app=bank.app_id,
        title='Compra', message='Compra R$ 10 em Loja ' + payload + ' no cartão final 0001')
    NotificationTitlePreference.objects.create(user=users[0], title=NotificationTitle.objects.get(title='Compra'), enabled=True)
    Version.objects.create(version='security-tests', date=today)
    AppConfig.get_solo()
    return dict(account=accounts[0].pk, foreign_account=accounts[1].pk, card=cards[0].pk,
                number=numbers[0].pk, foreign_number=numbers[1].pk, category=category.pk,
                subcategory=subcategory.pk, plan=plan.pk, notification=notification.pk,
                legacy=legacy.pk, transaction=own_transaction.pk, disabled_token=device.token,
                other_user=users[1].pk, bank=bank.pk, account_type=kind.pk, date=today.isoformat(),
                own_notification=own_notification.pk)


def run_browser(base, data, output):
    from playwright.sync_api import sync_playwright, expect
    results = []
    def passed(name):
        results.append(name)
        print('PASS:', name, flush=True)
        (output / 'results.json').write_text(json.dumps(results, indent=2))

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 1000})
        # Tests do not depend on third-party fonts, icons or chart CDNs.
        context.route('**/*', lambda route: route.continue_() if route.request.url.startswith(base) else route.abort())
        page = context.new_page()
        page.goto('/login/')
        page.locator('#id_username').fill('owner')
        page.locator('#id_password').fill('Browser!valid-7P-oak')
        page.locator('input[type=submit]').click()
        page.wait_for_url('**/mes_atual/')
        passed('Login real com sessão')

        page.goto('/relatorio_financeiro/saida/cadastrar/')
        numbers = page.evaluate('window.card_numbers_json')
        assert data['foreign_number'] not in [row['id'] for row in numbers]
        assert 'PRIVATE-FOREIGN-CARD' not in page.content()
        assert page.evaluate('window.__xss || 0') == 0
        assert page.locator('img[onerror]').count() == 0
        page.screenshot(path=str(output / 'transaction-form-safe-json.png'), full_page=True)
        passed('S07/S08: formulário sem cartão alheio e JSON com payload inerte')

        page.locator('#id_payment_method').select_option('2')
        page.locator('#id_account').select_option(str(data['account']))
        page.locator('#id_category').select_option(str(data['category']), force=True)
        page.locator(f'#id_subcategory option[value="{data["subcategory"]}"]').wait_for(state='attached')
        page.locator('#id_subcategory').select_option(str(data['subcategory']), force=True)
        page.locator('#id_posted_date').fill(data['date'])
        page.locator('#id_payment_date').fill(data['date'])
        page.locator('#id_description').fill('Created through browser')
        page.locator('#id_value').fill('12.34')
        page.locator('form input[type=submit]').click()
        page.wait_for_url('**/mes_atual/')
        passed('Fluxo legítimo: cadastro financeiro pela tela')

        def fetch(path, method='GET', body=None):
            return page.evaluate('''async ({path, method, body}) => {
                const csrf = document.cookie.split('; ').find(x => x.startsWith('csrftoken='))?.split('=')[1];
                const response = await fetch(path, {method, credentials: 'same-origin',
                    headers: {'Content-Type':'application/json', 'X-CSRFToken': csrf || ''},
                    body: body === null ? undefined : JSON.stringify(body)});
                return {status: response.status, text: await response.text()};
            }''', {'path': path, 'method': method, 'body': body})

        body = dict(description='Invalid relation', value=10, posted_date=data['date'],
                    category=data['category'], subcategory=data['subcategory'], account=data['foreign_account'])
        assert fetch('/api/transactions/', 'POST', body)['status'] == 400
        response = fetch('/api/transactions/?expand=account')
        assert response['status'] == 200
        assert 'PRIVATE-ACCOUNT-2' not in response['text']
        assert next(row for row in json.loads(response['text']) if row['id'] == data['legacy'])['account'] is None
        passed('S01: escrita alheia bloqueada e expansão legada protegida via sessão/CSRF')

        response = fetch(f'/api/notifications/{data["notification"]}/', 'PATCH', {'is_used': True})
        assert response['status'] == 404 and 'PRIVATE-MESSAGE' not in response['text']
        passed('S02: PATCH alheio sem leitura ou alteração')

        response = fetch(f'/api/accounts/{data["account"]}/', 'PUT', {'user': data['other_user']})
        assert response['status'] == 400
        passed('S03: troca de proprietário bloqueada')

        assert fetch('/api/categories/', 'POST', {'type': 'saida', 'description': 'Forbidden'})['status'] == 403
        passed('S04: usuário comum não escreve em catálogo global')

        anonymous = browser.new_context(base_url=base)
        response = anonymous.request.get('/api/accounts/', headers={'Authorization': 'Bearer ' + data['disabled_token']})
        assert response.status in (401, 403)
        anonymous.close()
        passed('S05: dispositivo de usuário desativado rejeitado em HTTP real')

        response = page.goto(f'/relatorio_financeiro/parcelamento/editar/{data["plan"]}/')
        assert response.status == 404 and 'PRIVATE-PLAN' not in page.content()
        page.screenshot(path=str(output / 'foreign-installment-404.png'), full_page=True)
        passed('S06/S09: tela alheia 404 sem conteúdo privado ou debug')

        page.goto('/relatorio_financeiro/saida/cadastrar/')
        page.evaluate('''async () => {
            const {renderTable} = await import('/static/js/layout/elements/tables.js');
            const target = document.createElement('div'); target.id = 'security-table'; document.body.appendChild(target);
            renderTable(target, [{id: 1, posted_date: '2026-11-05', description: '<img src=x onerror=window.__xss=3>',
                category: 1, subcategory: 1, value: 10, currency: 'BRL', account: 1}],
                {cards: [], accounts: [{id: 1, bank: 1}], banks: [{id: 1, icon: '/static/img/logo.png'}],
                 category: {description: 'Test'}, subcategories: [{id: 1, name: 'Test'}]});
            window.showModal('Texto seguro', '<img src=x onerror=window.__xss=4>');
        }''')
        assert page.locator('#security-table img[onerror]').count() == 0
        assert page.locator('#modal-body img').count() == 0
        assert page.evaluate('window.__xss || 0') == 0
        page.screenshot(path=str(output / 'xss-table-modal-text.png'), full_page=True)
        passed('S08: tabela e modal reais mostram payload como texto')

        page.goto('/relatorio_financeiro/importar/?fonte=notifications')
        notifications = page.evaluate('window.myFinance.notifications')
        assert data['own_notification'] in [row['id'] for row in notifications]
        assert 'PRIVATE-MESSAGE' not in page.content()
        assert page.locator('img[onerror]').count() == 0
        assert page.evaluate('window.__xss || 0') == 0
        page.screenshot(path=str(output / 'import-notifications-safe-json.png'), full_page=True)
        passed('S08: tela de importação preserva notificações como dados, sem executar HTML')

        registration = browser.new_context(base_url=base)
        registration.route('**/*', lambda route: route.continue_() if route.request.url.startswith(base) else route.abort())
        signup = registration.new_page()
        signup.goto('/usuarios/cadastrar/')
        for field, value in dict(username='browser-new', name='Browser New', email='new@browser.invalid',
                                 password1='1', password2='1').items():
            signup.locator('#id_' + field).fill(value)
        signup.locator('input[type=submit]').click()
        assert '/usuarios/cadastrar/' in signup.url
        expect(signup.locator('.errorlist')).not_to_have_count(0)
        signup.screenshot(path=str(output / 'weak-password-rejected.png'), full_page=True)
        for field in ('password1', 'password2'):
            signup.locator('#id_' + field).fill('Cedar!9V-river-4Y')
        signup.locator('input[type=submit]').click()
        signup.wait_for_url('**/login/')
        passed('S11: tela rejeita senha fraca e aceita cadastro com senha forte')
        registration.close()

        staff = browser.new_context(base_url=base)
        staff.route('**/*', lambda route: route.continue_() if route.request.url.startswith(base) else route.abort())
        admin = staff.new_page()
        admin.goto('/login/')
        admin.locator('#id_username').fill('staff')
        admin.locator('#id_password').fill('Browser!valid-7P-oak')
        admin.locator('input[type=submit]').click()
        admin.wait_for_url('**/mes_atual/')
        admin.goto('/relatorio_financeiro/configuracoes/categorias/cadastrar/')
        admin.locator('#id_type').select_option('saida')
        admin.locator('#id_description').fill('Created by staff UI')
        admin.locator('input[type=submit]').click()
        admin.wait_for_url('**/configuracoes/')
        passed('S04: administrador continua criando categoria pela tela')
        staff.close()
        context.close()
        browser.close()
    return results


def main():
    output = Path('/tmp/myfinance-security-browser-results')
    output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='myfinance-security-browser-') as directory:
        os.environ['MYFINANCE_E2E_DIRECTORY'] = directory
        os.environ['DJANGO_SETTINGS_MODULE'] = 'myfinance.security_test_settings'
        data = seed()
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        base = f'http://127.0.0.1:{port}'
        with (output / 'server.log').open('w') as log:
            server = subprocess.Popen([sys.executable, 'manage.py', 'runserver', f'127.0.0.1:{port}',
                                       '--noreload', '--insecure'], cwd=ROOT, stdout=log, stderr=log)
            try:
                for _ in range(100):
                    try:
                        with urlopen(base + '/login/', timeout=1):
                            break
                    except OSError:
                        if server.poll() is not None:
                            raise RuntimeError('Test server failed; see ' + str(output / 'server.log'))
                        time.sleep(0.1)
                else:
                    raise RuntimeError('Test server did not become ready.')
                results = run_browser(base, data, output)
                print(f'{len(results)} browser scenarios passed. Artifacts: {output}', flush=True)
            finally:
                server.terminate()
                server.wait(timeout=10)


if __name__ == '__main__':
    main()
