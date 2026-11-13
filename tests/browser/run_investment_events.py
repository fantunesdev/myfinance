"""Exercise reconciliation UI with disposable synthetic data; never uses production settings.

PLAYWRIGHT_BROWSERS_PATH=/tmp/myfinance-playwright .venv/bin/python tests/browser/run_investment_events.py
Screenshots and results: /tmp/myfinance-investment-events-browser-results.
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

    django.setup()
    from datetime import date, timedelta
    from uuid import uuid4
    from django.core.management import call_command
    from django.test import Client
    from django.utils import timezone
    from bank_sync.models import (
        BankConnection,
        ExternalInvestment,
        InvestmentCashEvidence,
        InvestmentEvent,
        InvestmentHistoryJob,
        InvestmentReconciliationBaseline,
        ReconciledInvestmentOperation,
    )
    from investments.models import Asset, Investment, InvestmentTransaction as Movement
    from investments.services.transaction import InvestmentTransactionService as Service
    from login.models import User, Profile
    from statement.models import AppConfig, Currency, Version

    call_command('migrate', verbosity=0)
    AppConfig.get_solo()
    Currency.objects.get_or_create(pk='BRL', defaults={'description': 'Real', 'symbol': 'R$'})
    Version.objects.create(version='browser-test', date=date(2026, 11, 13))
    result = {}
    for username in ['resolved-demo', 'pending-demo']:
        user = User.objects.create_user(
            username=username, name=username, email=f'{username}@browser.invalid', password='Synthetic!only-721'
        )
        Profile.objects.create(user=user)
        wallet = Service.get_or_create_default_wallet(user)
        asset = Asset.objects.create(
            user=user, description='Ação de teste', symbol='TEST3', asset_type='variable_income'
        )
        investment = Investment.objects.create(
            user=user, asset=asset, broker=wallet.broker, description='Ação TEST3', start_date=date(2020, 1, 1)
        )
        Movement.objects.create(
            user=user, investment=investment, date=date(2026, 1, 1), type='aporte', amount=1000, quantity=100
        )
        funding = Movement.objects.create(
            user=user, investment=wallet, date=date(2026, 11, 1), type='aporte', amount=200
        )
        connection = BankConnection.objects.create(user=user, item_id=uuid4())
        source = ExternalInvestment.objects.create(
            connection=connection,
            external_id=uuid4(),
            investment=investment,
            facts={'name': 'TEST3', 'currencyCode': 'BRL'},
        )
        InvestmentReconciliationBaseline.objects.create(
            investment=investment, date=date(2026, 11, 11), evidence='Abertura sintética'
        )
        job = InvestmentHistoryJob.objects.create(
            connection=connection, state='succeeded', finished_at=timezone.now(), progress={'events': 93}
        )

        def event(state, day, kind='INTEREST', amount=10, quantity=None, description=None):
            row = InvestmentEvent.objects.create(
                connection=connection,
                external_id=str(uuid4()),
                state=state,
                last_seen_job=job,
                facts={
                    'date': day + 'T00:00:00Z',
                    'tradeDate': day + 'T00:00:00Z',
                    'type': kind,
                    'amount': amount,
                    'netAmount': amount,
                    'quantity': quantity,
                    'value': 10,
                    'description': description,
                },
            )
            row.investments.add(source)
            return row

        def cash(amount, kind='CREDIT'):
            return InvestmentCashEvidence.objects.create(
                connection=connection,
                external_id=str(uuid4()),
                account_id=uuid4(),
                facts={
                    'date': '2026-11-13T10:00:00Z',
                    'type': kind,
                    'amount': amount if kind == 'CREDIT' else -amount,
                    'description': 'Crédito Evento B3 TEST3' if kind == 'CREDIT' else 'Débito B3 de duas compras',
                    'currencyCode': 'BRL',
                    'status': 'POSTED',
                },
            )

        info = {'funding': funding.pk}
        if username == 'resolved-demo':
            for i in range(93):
                day = (date(2026, 11, 1) - timedelta(days=i)).isoformat()
                row = event(
                    'applied' if i < 90 else 'linked',
                    day,
                    'SELL' if i == 0 else 'INTEREST',
                    description='Rendimento <img src=x onerror="window.__xss=1">' if i == 0 else None,
                )
                operation = ReconciledInvestmentOperation.objects.create(
                    event=row, kind='income', state=row.state, evidence='Conferido no extrato de teste'
                )
                movement = Movement.objects.create(
                    user=user, investment=investment, date=day, type='rendimento', amount=10, affects_value=False
                )
                operation.movements.add(movement)
                receipt = cash(10)
                receipt.facts['date'] = day + 'T10:00:00Z'
                receipt.save()
                operation.cash_evidence.add(receipt)
        else:
            historical = event('historical', '2026-10-10')
            conflict = event('conflict', '2026-10-15')
            operation = ReconciledInvestmentOperation.objects.create(
                event=conflict, kind='income', state='conflict', evidence='Líquido anterior'
            )
            old = Movement.objects.create(
                user=user,
                investment=investment,
                date=date(2026, 10, 15),
                type='rendimento',
                amount=9,
                affects_value=False,
            )
            operation.movements.add(old)
            income = event('new', '2026-11-13', amount=10)
            buy1 = event('new', '2026-11-13', kind='BUY', amount=40, quantity=4)
            buy2 = event('new', '2026-11-13', kind='BUY', amount=60, quantity=6)
            bank_income = cash(10)
            bank_buy = cash(101, 'DEBIT')
            info.update(
                historical=historical.pk,
                conflict=conflict.pk,
                income=income.pk,
                buy1=buy1.pk,
                buy2=buy2.pk,
                bank_income=bank_income.pk,
                bank_buy=bank_buy.pk,
            )
        client = Client()
        client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')
        info['session'] = client.cookies['sessionid'].value
        result[username] = info
    return result


def run_browser(base, data, output):
    from playwright.sync_api import sync_playwright, expect

    results = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)

        def context(name, width=1360):
            ctx = browser.new_context(
                base_url=base, viewport={'width': width, 'height': 960}, timezone_id='America/Sao_Paulo'
            )
            ctx.add_cookies([{'name': 'sessionid', 'value': data[name]['session'], 'url': base}])
            ctx.route('**/*', lambda route: route.continue_() if route.request.url.startswith(base) else route.abort())
            return ctx

        resolved = context('resolved-demo')
        page = resolved.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto('/investimentos/conciliacao/')
        expect(page.locator('#pending-count')).to_have_text('0')
        expect(page.locator('#resolved-count')).to_have_text('93')
        expect(page.locator('#empty-title')).to_have_text('Nenhum evento precisa de revisão')
        assert page.locator('.reconciliation-event').count() == 0
        expect(page.locator('#event-pagination')).to_be_hidden()
        page.screenshot(path=str(output / 'empty-pending-desktop.png'), full_page=True)
        results.append('Default: zero pendências, histórico separado com 93 concluídos')
        page.locator('#show-history').click()
        expect(page.locator('.reconciliation-event')).to_have_count(20)
        expect(page.locator('#event-count')).to_contain_text('de 93 eventos concluídos')
        page.locator('.reconciliation-event > summary').first.click()
        expect(page.locator('.reconciliation-event').first).to_contain_text('Provento')
        expect(page.locator('.reconciliation-event').first).to_contain_text('Lançamentos vinculados')
        assert page.locator('.reconciliation-form').count() == 0
        page.locator('.reconciliation-facts > summary').first.click()
        assert page.locator('img[onerror]').count() == 0
        assert page.evaluate('window.__xss || 0') == 0
        page.screenshot(path=str(output / 'history-desktop.png'), full_page=True)
        page.locator('#next-page').click()
        expect(page.locator('#page-label')).to_have_text('2 de 5')
        page.locator('#next-page').click()
        page.locator('#next-page').click()
        expect(page.locator('#page-label')).to_have_text('4 de 5')
        page.locator('#next-page').click()
        expect(page.locator('.reconciliation-event')).to_have_count(13)
        expect(page.locator('#next-page')).to_be_disabled()
        results.append('Histórico paginado, provento corrigido e detalhes sem formulários nem HTML executável')
        page.set_viewport_size({'width': 390, 'height': 844})
        page.locator('[data-view="pending"]').click()
        expect(page.locator('#event-empty')).to_be_visible()
        page.screenshot(path=str(output / 'empty-pending-mobile.png'), full_page=True)
        page.locator('[data-view="resolved"]').click()
        expect(page.locator('.reconciliation-event')).to_have_count(20)
        page.locator('.reconciliation-event > summary').first.click()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        card = page.locator('.reconciliation-event').first.bounding_box()
        assert card['x'] >= 12 and card['x'] + card['width'] <= 378
        expect(page.locator('.reconciliation-back')).to_be_visible()
        page.screenshot(path=str(output / 'history-mobile.png'), full_page=True)
        results.append('Página responsiva em 390px sem rolagem horizontal')
        pending = context('pending-demo')
        p = pending.new_page()
        p.on('pageerror', lambda error: errors.append(str(error)))
        ids = data['pending-demo']
        p.goto('/investimentos/conciliacao/')
        expect(p.locator('#pending-count')).to_have_text('5')
        historical = p.locator('details[data-review]').filter(has=p.locator(f'#event-{ids["historical"]}-action'))
        # Forms are built only after opening their summary.
        p.locator('.reconciliation-event > summary').filter(has_text='10/10/2026').click()
        historical = p.locator('.reconciliation-event').filter(has=p.locator(f'#event-{ids["historical"]}-action'))
        assert historical.locator('option[value="apply"]').count() == 0
        expect(historical.locator(f'#event-{ids["historical"]}-cash')).to_be_hidden()
        historical.locator(f'#event-{ids["historical"]}-action').select_option('ignore')
        historical.locator(f'#event-{ids["historical"]}-evidence').fill(
            'Evento sintético sem efeito na carteira, conferido no teste.'
        )
        historical.get_by_role('button', name='Ignorar evento').click()
        expect(p.locator('#pending-count')).to_have_text('4')
        results.append('Evento histórico oferece só vínculo/justificativa; confirmação CSRF move o evento ao histórico')
        conflict_summary = p.locator('.reconciliation-event > summary').filter(has_text='15/10/2026')
        conflict_summary.click()
        conflict = p.locator('.reconciliation-event').filter(has=p.locator(f'#event-{ids["conflict"]}-action'))
        expect(conflict.locator(f'#event-{ids["conflict"]}-action option')).to_have_count(1)
        expect(conflict.locator(f'#event-{ids["conflict"]}-action')).to_have_value('keep')
        conflict.get_by_role('button', name='Fechar revisão').click()
        # Locate new events by their amounts; all have the same date and title.
        p.locator('.reconciliation-event > summary').filter(has_text='40,00').click()
        p.locator('.reconciliation-event > summary').filter(has_text='60,00').click()
        first = p.locator('.reconciliation-event').filter(has=p.locator(f'#event-{ids["buy1"]}-action'))
        second = p.locator('.reconciliation-event').filter(has=p.locator(f'#event-{ids["buy2"]}-action'))
        expect(first.locator(f'#event-{ids["buy1"]}-principal')).to_be_hidden()
        expect(first.locator(f'#event-{ids["buy1"]}-fee')).to_be_hidden()
        first.locator('.group-event').check()
        second.locator('.group-event').check()
        expect(first.locator(f'#event-{ids["buy1"]}-fee')).to_be_visible()
        first.locator(f'#event-{ids["buy1"]}-cash').select_option(str(ids['bank_buy']))
        first.locator('[data-credit]').select_option(str(ids['funding']))
        first.locator('[data-amount]').fill('101')
        first.locator(f'#event-{ids["buy1"]}-fee').fill('1')
        first.locator(f'#event-{ids["buy1"]}-evidence').fill(
            'Nota sintética: duas compras e R$1 de custo, uma liquidação bancária.'
        )
        first.get_by_role('button', name='Confirmar 2 eventos selecionados').click()
        expect(p.locator('#pending-count')).to_have_text('2')
        results.append(
            'Compras exibem só os campos pertinentes e agrupam duas ordens com débito/custo/origem comprovados'
        )
        p.locator('.reconciliation-event > summary').filter(has_text='13/11/2026').click()
        income = p.locator('.reconciliation-event').filter(has=p.locator(f'#event-{ids["income"]}-action'))
        expect(income.locator(f'#event-{ids["income"]}-principal')).to_be_hidden()
        expect(income.locator('[data-credit]')).to_be_hidden()
        income.locator(f'#event-{ids["income"]}-cash').select_option(str(ids['bank_income']))
        income.locator(f'#event-{ids["income"]}-evidence').fill('Provento sintético comprovado pelo crédito bancário.')
        inflight_checks = []
        def income_request(route):
            disabled = p.evaluate("""id => {
                const action = document.getElementById(`event-${id}-action`);
                action.dispatchEvent(new Event('change'));
                return action.closest('form').querySelector('[type=submit]').disabled;
            }""", ids['income'])
            inflight_checks.append(disabled)
            route.continue_()
        p.route(f'**/conciliacao/{ids["income"]}/', income_request)
        income.get_by_role('button', name='Registrar operação').click()
        expect(p.locator('#pending-count')).to_have_text('1')
        assert inflight_checks == [True]
        results.append('Provento novo dispensa principal e origem de compra; aplicação legítima atualiza contadores')
        p.locator('[data-view="resolved"]').click()
        expect(p.locator('#event-count')).to_contain_text('eventos concluídos')
        p.locator('.reconciliation-event > summary').filter(has_text='40,00').click()
        group_history = p.locator('.reconciliation-event').filter(has_text='40,00')
        expect(group_history).to_contain_text('Esta conciliação reúne 2 eventos')
        assert group_history.locator('form').count() == 0
        results.append('Histórico explica liquidações compartilhadas sem apresentar um formulário de revisão')
        p.locator('[data-view="pending"]').click()
        p.locator('.reconciliation-event > summary').filter(has_text='15/10/2026').click()
        draft = p.locator(f'#event-{ids["conflict"]}-evidence')
        draft.fill('Conferência em andamento; preservar este texto.')
        polls = {'count': 0}

        def polling(route):
            response = route.fetch()
            payload = response.json()
            polls['count'] += 1
            payload['jobs'][0]['state'] = 'running'
            payload['jobs'][0]['progress'] = {'titles': 1, 'total_titles': 2}
            if polls['count'] >= 2:
                payload['events'][0]['reason'] = 'A instituição complementou o evento durante a revisão.'
            route.fulfill(response=response, json=payload)

        import re

        p.route(re.compile(r'/conciliacao/eventos/\?'), polling)
        p.locator('#history-collect').click()
        expect(p.locator('#event-updates')).to_be_visible(timeout=8000)
        expect(draft).to_have_value('Conferência em andamento; preservar este texto.')
        p.get_by_role('button', name='Fechar revisão').click()
        expect(p.locator('#event-updates')).to_be_hidden()
        results.append('Consulta em segundo plano preserva a revisão aberta e atualiza a lista ao fechá-la')
        assert not errors, errors
        browser.close()
    (output / 'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2))
    for result in results:
        print('PASS:', result, flush=True)


def main():
    output = Path('/tmp/myfinance-investment-events-browser-results')
    output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='myfinance-investment-events-') as temporary:
        os.environ['MYFINANCE_E2E_DIRECTORY'] = temporary
        os.environ['DJANGO_SETTINGS_MODULE'] = 'myfinance.security_test_settings'
        data = seed()
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            port = listener.getsockname()[1]
        base = f'http://127.0.0.1:{port}'
        with (output / 'server.log').open('w') as log:
            server = subprocess.Popen(
                [sys.executable, 'manage.py', 'runserver', f'127.0.0.1:{port}', '--noreload', '--insecure'],
                cwd=ROOT,
                env=os.environ.copy(),
                stdout=log,
                stderr=log,
            )
            try:
                for unused in range(100):
                    try:
                        urlopen(base + '/login/', timeout=1).close()
                        break
                    except OSError:
                        time.sleep(0.1)
                run_browser(base, data, output)
            finally:
                server.terminate()
                server.wait(timeout=10)


if __name__ == '__main__':
    main()
