"""Check the photo gallery using disposable data under /tmp.

PLAYWRIGHT_BROWSERS_PATH=/tmp/myfinance-playwright .venv/bin/python tests/browser/run_dream_photos.py
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


def run():
    with tempfile.TemporaryDirectory(prefix='myfinance-dream-photos-') as directory:
        os.environ['MYFINANCE_E2E_DIRECTORY'] = directory
        os.environ['DJANGO_SETTINGS_MODULE'] = 'myfinance.security_test_settings'
        import django

        django.setup()
        from datetime import date
        from django.core.management import call_command
        from django.test import Client
        from PIL import Image
        from playwright.sync_api import expect, sync_playwright
        from login.models import Profile, User
        from statement.models import AppConfig, Currency, Dream, Version

        call_command('migrate', verbosity=0)
        call_command('collectstatic', verbosity=0, interactive=False)
        AppConfig.get_solo()
        Currency.objects.get_or_create(pk='BRL', defaults={'description': 'Real', 'symbol': 'R$'})
        Version.objects.create(version='browser-test', date=date(2026, 11, 22))
        user = User.objects.create_user(
            username='gallery-demo',
            email='gallery@browser.invalid',
            name='Demo',
        )
        Profile.objects.create(user=user)
        dream = Dream.objects.create(
            user=user,
            description='Viagem dos sonhos',
            target_value=10000,
            limit_date=date(2027, 12, 1),
        )
        client = Client()
        client.force_login(user)
        images = []
        for number, color in enumerate(['#276b8c', '#55864a', '#c87842']):
            path = Path(directory) / f'photo-{number}.png'
            Image.new('RGB', (900, 600), color).save(path)
            images.append(str(path))
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        origin = f'http://127.0.0.1:{port}'
        log = open(Path(directory) / 'server.log', 'w+')
        server = subprocess.Popen(
            [
                sys.executable,
                'manage.py',
                'runserver',
                f'127.0.0.1:{port}',
                '--noreload',
                '--insecure',
            ],
            cwd=ROOT,
            env=os.environ.copy(),
            stdout=log,
            stderr=log,
        )
        try:
            for _ in range(100):
                try:
                    urlopen(origin + '/login/', timeout=1).close()
                    break
                except Exception:
                    if server.poll() is not None:
                        log.seek(0)
                        raise RuntimeError(log.read())
                    time.sleep(0.1)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(viewport={'width': 1440, 'height': 1000}, has_touch=True)
                context.add_cookies(
                    [
                        {
                            'name': 'sessionid',
                            'value': client.cookies['sessionid'].value,
                            'url': origin,
                        }
                    ]
                )
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(f'{origin}/sonhos/{dream.pk}/')
                expect(page.get_by_text('Nenhuma foto ainda.', exact=False)).to_be_visible()
                expect(page.get_by_role('heading', name='Galeria')).to_be_visible()
                expect(page.locator('#dream-photo-upload')).to_be_hidden()
                page.get_by_role('button', name='Adicionar fotos', exact=True).click()
                expect(page.locator('#dream-photo-upload')).to_be_visible()
                page.get_by_role('button', name='Adicionar fotos', exact=True).click()
                expect(page.locator('#dream-photo-upload')).to_be_hidden()
                page.get_by_role('button', name='Adicionar fotos', exact=True).click()
                page.locator('input[name=photos]').set_input_files(images)
                expect(page.locator('[data-photo-selection]')).to_have_text('3 fotos selecionadas')
                expect(page.locator('.dream-photo-picker')).to_be_visible()
                page.get_by_role('button', name='Adicionar selecionadas').click()
                expect(page.locator('.dream-photo-card')).to_have_count(3)
                expect(page.locator('#dream-photo-upload')).to_be_hidden()
                assert page.locator('.dream-photos button:not(.btn), .dream-photo-dialog button:not(.btn)').count() == 0
                cards = page.locator('.dream-photo-card')
                original_ids = cards.evaluate_all('cards => cards.map(card => card.dataset.photoId)')
                with page.expect_response(lambda response: '/fotos/ordenar/' in response.url) as saved:
                    cards.first.drag_to(cards.last, target_position={'x': 120, 'y': 40})
                assert saved.value.status == 200
                expected_ids = original_ids[1:] + original_ids[:1]
                assert cards.evaluate_all('cards => cards.map(card => card.dataset.photoId)') == expected_ids
                page.reload()
                assert cards.evaluate_all('cards => cards.map(card => card.dataset.photoId)') == expected_ids
                page.route('**/fotos/ordenar/', lambda route: route.fulfill(status=500, body='Error'))
                cards.first.locator('a').focus()
                page.keyboard.press('Alt+ArrowRight')
                expect(page.locator('.dream-photo-order-status')).to_be_visible()
                assert cards.evaluate_all('cards => cards.map(card => card.dataset.photoId)') == expected_ids
                page.unroute('**/fotos/ordenar/')
                cards.first.locator('a').focus()
                with page.expect_response(lambda response: '/fotos/ordenar/' in response.url):
                    page.keyboard.press('Alt+ArrowRight')
                expect(page.locator('.dream-photo-grid')).not_to_have_attribute('aria-busy', 'true')
                page.locator('.dream-photo-open').first.click()
                first_image = page.locator('.dream-photo-open').first.evaluate('el => el.href')
                expect(page.locator('.dream-photo-slide').first.locator('img')).to_have_attribute('src', first_image)
                page.keyboard.press('Escape')
                page.locator('.dream-photo-open').nth(1).click()
                dialog = page.locator('.dream-photo-dialog')
                expect(dialog).to_be_visible()
                expect(page.locator('[data-photo-counter]')).to_have_text('2 de 3')
                page.locator('.dream-photo-slide').nth(1).locator('a').click()
                expect(dialog).to_have_class('dream-photo-dialog is-fullscreen')
                page.wait_for_function('document.fullscreenElement !== null')
                expect(page.get_by_role('button', name='Sair da tela inteira')).to_be_visible()
                assert page.locator('.dream-photo-slide').nth(1).locator('img').evaluate(
                    'el => Math.abs(el.getBoundingClientRect().height - window.innerHeight) < 2'
                )
                page.get_by_role('button', name='Sair da tela inteira').click()
                page.wait_for_function('document.fullscreenElement === null')
                expect(dialog).not_to_have_class('dream-photo-dialog is-fullscreen')
                assert (
                    page.locator('.dream-photo-track').evaluate('el => getComputedStyle(el).transitionDuration')
                    == '0.35s'
                )
                page.get_by_role('button', name='Próxima foto', exact=True).click()
                expect(page.locator('[data-photo-counter]')).to_have_text('3 de 3')
                expect(page.locator('[data-photo-next]')).to_be_disabled()
                page.keyboard.press('ArrowLeft')
                expect(page.locator('[data-photo-counter]')).to_have_text('2 de 3')
                page.keyboard.press('Escape')
                expect(dialog).not_to_be_visible()
                expect(page.locator('.dream-photo-open').nth(1)).to_be_focused()
                page.locator('.dream-photos').screenshot(path='/tmp/myfinance-dream-photos-desktop.png')
                page.set_viewport_size({'width': 390, 'height': 844})
                page.locator('.dream-photo-open').first.click()
                expect(page.locator('[data-photo-prev]')).to_be_disabled()
                assert dialog.evaluate('el => el.scrollWidth <= el.clientWidth')
                page.evaluate("document.querySelector('.dream-photo-viewer').requestFullscreen = undefined")
                page.locator('.dream-photo-slide').first.locator('a').click()
                expect(dialog).to_have_class('dream-photo-dialog is-fullscreen')
                assert abs(dialog.bounding_box()['height'] - page.viewport_size['height']) < 2
                page.keyboard.press('Escape')
                expect(dialog).to_be_visible()
                expect(dialog).not_to_have_class('dream-photo-dialog is-fullscreen')
                stage = page.locator('.dream-photo-stage')
                bounds = stage.bounding_box()
                cdp = context.new_cdp_session(page)
                y = bounds['y'] + bounds['height'] / 2
                cdp.send(
                    'Input.dispatchTouchEvent',
                    {
                        'type': 'touchStart',
                        'touchPoints': [{'x': 300, 'y': y}],
                    },
                )
                cdp.send(
                    'Input.dispatchTouchEvent',
                    {
                        'type': 'touchMove',
                        'touchPoints': [{'x': 100, 'y': y}],
                    },
                )
                cdp.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
                expect(page.locator('[data-photo-counter]')).to_have_text('2 de 3')
                page.locator('.dream-photo-track').evaluate(
                    'el => Promise.all(el.getAnimations().map(animation => animation.finished))'
                )
                page.screenshot(path='/tmp/myfinance-dream-photos-mobile.png')
                page.emulate_media(reduced_motion='reduce')
                assert (
                    page.locator('.dream-photo-track').evaluate('el => getComputedStyle(el).transitionDuration') == '0s'
                )
                page.get_by_role('button', name='Fechar fotos').click()
                page.emulate_media(reduced_motion='no-preference')
                page.clock.install()
                page.locator('.dream-photo-open').first.click()
                expect(page.locator('[data-photo-play]')).to_have_text('Pausar')
                page.clock.fast_forward(5000)
                expect(page.locator('[data-photo-counter]')).to_have_text('2 de 3')
                page.get_by_role('button', name='Pausar apresentação').click()
                page.clock.fast_forward(5000)
                expect(page.locator('[data-photo-counter]')).to_have_text('2 de 3')
                page.get_by_role('button', name='Reproduzir apresentação').click()
                page.clock.fast_forward(5000)
                expect(page.locator('[data-photo-counter]')).to_have_text('3 de 3')
                expect(page.locator('[data-photo-play]')).to_have_text('Reproduzir')
                page.get_by_role('button', name='Fechar fotos').click()
                page.get_by_role('button', name='Remover foto 1', exact=True).click()
                expect(page.locator('.dream-photo-card')).to_have_count(2)
                page.goto(f'{origin}/sonhos/editar/{dream.pk}/')
                editor = page.get_by_role('textbox', name='Anotações', exact=True)
                expect(editor).to_be_visible()
                expect(page.locator('textarea[name=notes]')).to_be_hidden()
                editor.fill('Viagem especial')

                def select_notes():
                    editor.evaluate('''el => {
                        const range = document.createRange();
                        range.selectNodeContents(el);
                        const selection = window.getSelection();
                        selection.removeAllRanges();
                        selection.addRange(range);
                    }''')

                for label, tag in [('Negrito', 'b'), ('Itálico', 'i'), ('Sublinhado', 'u')]:
                    select_notes()
                    page.get_by_role('button', name=label, exact=True).click()
                    expect(editor.locator(tag)).to_have_text('Viagem especial')
                select_notes()
                page.get_by_role('button', name='Limpar formatação', exact=True).click()
                expect(editor.locator('b, i, u')).to_have_count(0)
                select_notes()
                page.get_by_role('button', name='Lista', exact=True).click()
                expect(editor.locator('ul li')).to_have_text('Viagem especial')
                page.get_by_role('button', name='Lista numerada', exact=True).click()
                expect(editor.locator('ol li')).to_have_text('Viagem especial')
                page.get_by_role('button', name='Editar HTML').click()
                expect(page.locator('textarea[name=notes]')).to_be_visible()
                page.locator('textarea[name=notes]').fill(
                    '<b onclick="window.__notesXss=1">Viagem especial</b><br><i>Planejar</i>'
                    '<ul><li>Passagens</li></ul><script>window.__notesXss=1</script>'
                    '<img src=x onerror="window.__notesXss=1">'
                )
                page.get_by_role('button', name='Salvar', exact=True).click()
                page.goto(f'{origin}/sonhos/{dream.pk}/')
                notes = page.locator('.formatted-notes')
                expect(notes.locator('b')).to_have_text('Viagem especial')
                expect(notes.locator('li')).to_have_text('Passagens')
                assert 'onclick' not in notes.inner_html()
                assert page.evaluate('window.__notesXss === undefined')
                page.goto(f'{origin}/sonhos/editar/{dream.pk}/')
                expect(editor.locator('b')).to_have_text('Viagem especial')
                page.get_by_role('button', name='Editar HTML').click()
                page.locator('textarea[name=notes]').fill('<b>Texto</b><img src=x onerror="window.__notesXss=1">')
                page.get_by_role('button', name='Editar HTML').click()
                expect(editor.locator('b')).to_have_text('Texto')
                expect(editor.locator('img')).to_have_count(0)
                page.locator('[data-rich-text]').screenshot(path='/tmp/myfinance-dream-notes-editor.png')
                assert not errors, errors
                browser.close()
                print(
                    'PASS: gallery, ordering, carousel, fullscreen, notes editor, HTML source, formatting, persistence, HTML sanitization.'
                )
        finally:
            server.terminate()
            server.wait(timeout=10)
            log.close()


if __name__ == '__main__':
    run()
