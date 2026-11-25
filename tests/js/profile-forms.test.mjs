import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import vm from 'node:vm';

const source = await readFile(new URL('../../statement/static/js/pages/user/profile-forms.js', import.meta.url), 'utf8');
function setup(fetcher) {
    const events = {}, toasts = [], requests = [];
    const closeButton = { addEventListener() {}, disabled: false };
    const content = { contains: () => false, setAttribute() {} };
    const dialog = { showModal() {}, querySelector: () => closeButton, addEventListener() {} };
    const document = {
        getElementById: id => ({ 'profile-dialog': dialog, 'profile-dialog-content': content, 'profile-dialog-title': {} })[id],
        addEventListener: (name, callback) => { events[name] = callback; },
    };
    const window = { fetch: true, myFinanceToast: (message, level) => toasts.push({ message, level }), addEventListener() {} };
    class FormData {
        constructor(form) { this.values = new Map(form.values); }
        append(key, value) { this.values.set(key, value); }
        get(key) { return this.values.get(key); }
    }
    vm.runInNewContext(source, {
        document, window, location: { href: 'https://myfinance.invalid/usuarios/perfil/', origin: 'https://myfinance.invalid' },
        URL, URLSearchParams, FormData, WeakSet, Set, AbortController,
        fetch: async (url, options) => { requests.push({url, options}); return fetcher(url, options); },
    });
    function form(action = 'https://myfinance.invalid/usuarios/perfil/editar/') {
        const button = { name: 'action', value: 'disable', disabled: false, getAttribute() { return null; } };
        const file = { name: 'foto.png' };
        const form = { action, values: [['csrfmiddlewaretoken', 'csrf-secret'], ['photo', file]],
            matches: () => true, hasAttribute: () => true,
            getAttribute: key => key === 'method' ? 'post' : key === 'action' ? action : null, querySelectorAll: () => [button] };
        const event = { target: form, submitter: button, preventDefault() { this.prevented = true; } };
        return { form, button, file, event };
    }
    return { requests, toasts, form, submit: event => events.submit(event), closeButton };
}

test('AJAX carries CSRF, files and clicked action, and prevents duplicate submission while pending', async () => {
    let resolve;
    const page = setup(() => new Promise(done => { resolve = done; }));
    const { event, file, button } = page.form();
    const pending = page.submit(event);
    assert.equal(event.prevented, true);
    assert.equal(button.disabled, true);
    await page.submit(event);
    assert.equal(page.requests.length, 1);
    const { options } = page.requests[0];
    assert.equal(options.credentials, 'same-origin');
    assert.equal(options.headers['X-CSRFToken'], 'csrf-secret');
    assert.equal(options.body.get('photo'), file);
    assert.equal(options.body.get('action'), 'disable');
    assert.equal(options.headers['Content-Type'], undefined); // Browser supplies the multipart boundary.
    resolve({ url: event.target.action, ok: false, status: 403 });
    await pending;
    assert.equal(button.disabled, false);
    assert.equal(page.closeButton.disabled, false);
    assert.equal(page.toasts[0].level, 'error');
    assert.equal(page.toasts.some(toast => toast.level === 'success'), false);
});

test('network uncertainty never reports success or retries a mutation automatically', async () => {
    const page = setup(async () => { throw new Error('Conexão interrompida.'); });
    const { event, button } = page.form();
    await page.submit(event);
    assert.equal(page.requests.length, 1);
    assert.equal(page.toasts.length, 1);
    assert.equal(page.toasts[0].level, 'error');
    assert.equal(button.disabled, false);
});

test('expired sessions report an error and Google authorization remains a native navigation', async () => {
    const page = setup(async () => ({ url: 'https://myfinance.invalid/login/?next=/usuarios/perfil/', ok: true }));
    await page.submit(page.form().event);
    assert.match(page.toasts[0].message, /sessão expirou/);
    const oauth = page.form('https://myfinance.invalid/auth/login/google-oauth2/');
    await page.submit(oauth.event);
    assert.equal(oauth.event.prevented, undefined);
    assert.equal(page.requests.length, 1);
});

test('a button named action cannot replace the endpoint URL through DOM named properties', async () => {
    const endpoint = 'https://myfinance.invalid/usuarios/seguranca/2fa/configurar/';
    const page = setup(async () => ({ url: endpoint, ok: false, status: 403 }));
    const { event, form, button } = page.form(endpoint);
    form.action = button;
    await page.submit(event);
    assert.equal(String(page.requests[0].url), endpoint);
});
