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
    from investments.models import Asset, Broker, Investment, InvestmentTransaction as Movement
    from investments.services.transaction import InvestmentTransactionService as Service
    from login.models import User, Profile
    from statement.models import AppConfig, Currency, Version

    call_command('migrate', verbosity=0)
    AppConfig.get_solo()
    Currency.objects.get_or_create(pk='BRL', defaults={'description': 'Real', 'symbol': 'R$'})
    Version.objects.create(version='browser-test', date=date(2026, 11, 13))
    result = {}
    for username in ['resolved-demo', 'pending-demo', 'import-demo']:
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
            user=user, investment=investment, date=date(2026, 1, 1), type='aporte',
            amount=3000 if username == 'resolved-demo' else 1000, quantity=100
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
            for kind, description in [
                ('CREDIT', 'Resgate - Cdb Porq Obj Banco Inter S A'),
                ('DEBIT', 'Compra - Criptomoedas'),
            ]:
                receipt = cash(1184.90, kind)
                receipt.facts['description'] = description
                receipt.save()
                if kind == 'CREDIT':
                    movement = Movement.objects.create(
                        user=user, investment=investment, date=date(2026, 11, 13), type='resgate', amount=1184.90,
                    )
                    info.update(bank_receipt=receipt.pk, bank_movement=movement.pk)
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
        elif username == 'pending-demo':
            historical = event('historical', '2026-10-10')
            historical_movement = Movement.objects.create(
                user=user, investment=investment, date=date(2026, 10, 10),
                type='rendimento', amount=10, affects_value=False,
            )
            historical_extra = Movement.objects.create(
                user=user, investment=investment, date=date(2026, 10, 10),
                type='custo', amount=1, affects_value=False,
            )
            historical_cash = cash(10)
            historical_cash.facts['date'] = '2026-10-10T10:00:00Z'
            historical_cash.save()
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
            income = event('new', '2026-11-13', kind='SELL', amount=10, description='Rendimento')
            buy1 = event('new', '2026-11-13', kind='BUY', amount=40, quantity=4)
            buy2 = event('new', '2026-11-13', kind='BUY', amount=60, quantity=6)
            bank_income = cash(10)
            bank_buy = cash(101, 'DEBIT')
            automatic_event = event('new', '2026-11-13', kind='SELL', amount=20, quantity=2)
            operation_id = uuid4()
            Movement.objects.create(user=user, investment=investment, date=date(2026, 11, 13),
                                    type='resgate', amount=20, quantity=2, operation_id=operation_id)
            Movement.objects.create(user=user, investment=wallet, date=date(2026, 11, 13),
                                    type='aporte', amount=20, operation_id=operation_id)
            automatic_cash = cash(20)
            automatic_cash.facts['description'] = 'Crédito B3 - Venda TEST3'
            automatic_cash.save()
            info.update(
                historical=historical.pk,
                historical_movement=historical_movement.pk,
                historical_extra=historical_extra.pk,
                historical_cash=historical_cash.pk,
                conflict=conflict.pk,
                income=income.pk,
                buy1=buy1.pk,
                buy2=buy2.pk,
                bank_income=bank_income.pk,
                bank_buy=bank_buy.pk,
            )
        else:
            from django.utils.dateparse import parse_datetime
            from bank_sync.models import InvestmentSnapshot
            bank = Broker.objects.create(user=user, description='Inter', kind='bank')
            cdb_asset = Asset.objects.create(user=user, description='CDB Inter', asset_type='fixed_income')
            cdb = Investment.objects.create(user=user, asset=cdb_asset, broker=bank,
                description='CDB para reinvestimento', start_date=date(2026, 11, 15), status='closed')
            InvestmentReconciliationBaseline.objects.create(investment=cdb, date=date(2026, 11, 15), evidence='Abertura de teste')
            Movement.objects.create(user=user, investment=cdb, date=date(2026, 11, 15), type='aporte', amount=600, quantity=600)
            cdb_source = ExternalInvestment.objects.create(connection=connection, external_id=uuid4(), investment=cdb,
                reference_at=parse_datetime('2026-11-16T14:00:00Z'), facts={'name': 'CDB Inter', 'type': 'FIXED_INCOME',
                    'status': 'TOTAL_WITHDRAWAL', 'balance': '0', 'quantity': '0', 'currencyCode': 'BRL'})
            quote = Movement.objects.create(user=user, investment=cdb, date=date(2026, 11, 16),
                type='atualizacao', current_value=0, quantity=0)
            InvestmentSnapshot.objects.create(external=cdb_source, reference_at=cdb_source.reference_at,
                fingerprint=uuid4().hex, facts={'balance': '0', 'quantity': '0'}, movement=quote)
            sale = InvestmentEvent.objects.create(connection=connection, external_id=str(uuid4()), state='new', last_seen_job=job,
                facts={'date': '2026-11-16T00:00:00Z', 'type': 'SELL', 'quantity': 600,
                       'amount': 606, 'netAmount': 606, 'value': 1.01, 'expenses': {}})
            sale.investments.add(cdb_source)
            account = uuid4()
            for kind, value, description in [('CREDIT', 606, 'Resgate - CDB Inter'), ('DEBIT', -606, 'Compra - Criptomoedas')]:
                receipt = InvestmentCashEvidence.objects.create(connection=connection, external_id=str(uuid4()), account_id=account,
                    facts={'date': '2026-11-16T10:00:00Z', 'type': kind, 'amount': value, 'description': description,
                           'currencyCode': 'BRL', 'status': 'POSTED'})
                if kind == 'DEBIT':
                    info['purchase_debit'] = receipt.pk
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
        page.locator('[data-view="bank"]').click()
        expect(page.locator('#bank-count')).to_have_text('2')
        expect(page.locator('.reconciliation-event')).to_have_count(2)
        expect(page.locator('#investment-events')).to_contain_text('Compra - Criptomoedas')
        expect(page.locator('#investment-events')).to_contain_text('Resgate - Cdb')
        expect(page.locator('#investment-events')).to_contain_text('1.184,90')
        expect(page.locator('#investment-events')).to_contain_text('não identifica a moeda nem a quantidade')
        assert page.locator('.reconciliation-form').count() == 0
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.screenshot(path=str(output / 'bank-statement-mobile.png'), full_page=True)
        results.append('Resgate e compra de cripto visíveis pelo extrato sem inventar eventos ou alterar saldos')
        page.mouse.move(0, 0)
        assert page.locator('#history-collect').evaluate("e => getComputedStyle(e).backgroundColor") == 'rgb(94, 0, 0)'
        receipt_id = data['resolved-demo']['bank_receipt']
        redemption = page.locator('.reconciliation-event').filter(has_text='Resgate - Cdb')
        redemption.locator('summary').click()
        redemption.locator(f'#bank-{receipt_id}-action').select_option('link')
        redemption.locator(f'#bank-{receipt_id}-movement').select_option(str(data['resolved-demo']['bank_movement']))
        redemption.locator(f'#bank-{receipt_id}-evidence').fill('Resgate já registrado; vínculo ao comprovante de teste.')
        redemption.locator('button[type="submit"]').click()
        expect(page.locator('#bank-count')).to_have_text('1')
        page.locator('#bank-view').select_option('bank_history')
        expect(page.locator('#investment-events')).to_have_attribute('aria-busy', 'false')
        expect(page.locator('.reconciliation-event')).to_have_count(1)
        page.locator('.reconciliation-event summary').click()
        expect(page.locator('#investment-events')).to_contain_text('Resgate já registrado; vínculo ao comprovante de teste.')
        assert page.locator('.reconciliation-form').count() == 0
        page.screenshot(path=str(output / 'bank-reviewed-mobile.png'), full_page=True)
        results.append('Conferência de extrato vincula registro existente, preserva histórico e usa botões vermelhos')
        pending = context('pending-demo')
        p = pending.new_page()
        p.on('pageerror', lambda error: errors.append(str(error)))
        ids = data['pending-demo']
        p.goto('/investimentos/conciliacao/')
        expect(p.locator('#pending-count')).to_have_text('6')
        p.locator('#auto-link').click()
        expect(p.locator('#pending-count')).to_have_text('5')
        expect(p.locator('#event-action-status')).to_contain_text('1 eventos e 0 comprovantes vinculados automaticamente')
        p.locator('#auto-link').click()
        expect(p.locator('#event-action-status')).to_contain_text('0 eventos e 0 comprovantes vinculados automaticamente')
        expect(p.locator('#investment-events')).to_have_attribute('aria-busy', 'false')
        results.append('Correspondência inequívoca vinculada automaticamente; repetir não duplica lançamentos nem vínculos')
        historical = p.locator('details[data-review]').filter(has=p.locator(f'#event-{ids["historical"]}-action'))
        # Forms are built only after opening their summary.
        p.locator('.reconciliation-event > summary').filter(has_text='10/10/2026').click()
        historical = p.locator('.reconciliation-event').filter(has=p.locator(f'#event-{ids["historical"]}-action'))
        assert historical.locator('option[value="apply"]').count() == 0
        local_choice = historical.locator(f'#event-{ids["historical"]}-existing input[value="{ids["historical_movement"]}"]')
        extra_choice = historical.locator(f'#event-{ids["historical"]}-existing input[value="{ids["historical_extra"]}"]')
        bank_choice = historical.locator(f'#event-{ids["historical"]}-cash input[value="{ids["historical_cash"]}"]')
        p.set_viewport_size({'width': 390, 'height': 844})
        expect(local_choice).to_be_visible()
        p.screenshot(path=str(output / 'before-independent-selections-mobile.png'), full_page=True)
        local_choice.check()
        bank_choice.check()
        expect(local_choice).to_be_checked()
        extra_choice.check()
        expect(local_choice).to_be_checked()
        expect(bank_choice).to_be_checked()
        extra_choice.uncheck()
        bank_choice.uncheck()
        expect(local_choice).to_be_checked()
        bank_choice.check()
        historical.locator(f'#event-{ids["historical"]}-evidence').fill('Evento sintético já registrado, conferido no extrato.')
        expect(local_choice).to_be_checked()
        expect(bank_choice).to_be_checked()
        assert p.evaluate('document.documentElement.scrollWidth <= innerWidth')
        p.screenshot(path=str(output / 'independent-selections-mobile.png'), full_page=True)
        linked_payloads = []
        def historical_request(route):
            linked_payloads.append(route.request.post_data_json)
            route.continue_()
        p.route(f'**/conciliacao/{ids["historical"]}/', historical_request)
        historical.get_by_role('button', name='Vincular lançamento').click()
        expect(p.locator('#pending-count')).to_have_text('4')
        assert linked_payloads[0]['movement_ids'] == [ids['historical_movement']]
        assert linked_payloads[0]['cash_ids'] == [ids['historical_cash']]
        p.set_viewport_size({'width': 1360, 'height': 960})
        results.append('Seleções independentes de lançamentos e liquidações persistem após foco e enviam ambos os IDs')
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
        first.locator(f'#event-{ids["buy1"]}-cash input[value="{ids["bank_buy"]}"]').check()
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
        income.locator(f'#event-{ids["income"]}-kind').select_option('income')
        expect(income.locator(f'#event-{ids["income"]}-principal')).to_be_hidden()
        expect(income.locator('[data-credit]')).to_be_hidden()
        income.locator(f'#event-{ids["income"]}-evidence').fill('Provento sintético comprovado pelo crédito bancário.')
        income.get_by_role('button', name='Registrar operação').click()
        expect(p.locator('#event-action-status')).to_contain_text('Marque a liquidação na conta bancária')
        expect(p.locator('#pending-count')).to_have_text('2')
        income.locator(f'#event-{ids["income"]}-cash input[value="{ids["bank_income"]}"]').check()
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
        imported = context('import-demo', width=390)
        purchase_page = imported.new_page()
        purchase_page.on('pageerror', lambda error: errors.append(str(error)))
        purchase_page.goto('/investimentos/conciliacao/')
        expect(purchase_page.locator('#pending-count')).to_have_text('1')
        purchase_page.locator('#auto-link').click()
        expect(purchase_page.locator('#pending-count')).to_have_text('0')
        expect(purchase_page.locator('#event-action-status')).to_contain_text('1 movimentações registradas')
        expect(purchase_page.locator('#investment-events')).to_have_attribute('aria-busy', 'false')
        purchase_page.locator('[data-view="bank"]').click()
        expect(purchase_page.locator('#investment-events')).to_have_attribute('aria-busy', 'false')
        expect(purchase_page.locator('#bank-count')).to_have_text('1')
        purchase_page.locator('.reconciliation-event summary').click()
        debit_id = data['import-demo']['purchase_debit']
        expect(purchase_page.locator(f'#bank-{debit_id}-action')).to_have_value('purchase')
        purchase_page.locator(f'#bank-{debit_id}-symbol').fill('BTC')
        purchase_page.locator(f'#bank-{debit_id}-quantity').fill('0.002')
        purchase_page.get_by_role('button', name='Registrar resgate e compra').click()
        expect(purchase_page.locator('#bank-count')).to_have_text('0')
        expect(purchase_page.locator('#event-action-status')).to_contain_text('Resgate e compra registrados')
        expect(purchase_page.locator('#investment-events')).to_have_attribute('aria-busy', 'false')
        purchase_page.locator('#bank-view').select_option('bank_history')
        expect(purchase_page.locator('#investment-events')).to_have_attribute('aria-busy', 'false')
        purchase_page.locator('.reconciliation-event summary').click()
        expect(purchase_page.locator('#investment-events')).to_contain_text('Bitcoin (Inter)')
        expect(purchase_page.locator('#investment-events')).to_contain_text('0,00200000 BTC')
        expect(purchase_page.locator('#investment-events')).to_contain_text('606,00')
        assert purchase_page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        purchase_page.screenshot(path=str(output / 'automatic-redemption-crypto-purchase-mobile.png'), full_page=True)
        results.append('Resgate importado automaticamente; só moeda e quantidade faltantes são confirmadas para registrar a compra de BTC')
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
