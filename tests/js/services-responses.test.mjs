import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import vm from 'node:vm';

const source = await readFile(new URL('../../statement/static/js/data/services.js', import.meta.url), 'utf8');
function setup(fetcher) {
    const requests = [], events = [];
    const context = vm.createContext({
        document: { cookie: 'csrftoken=test-csrf' },
        window: { dispatchEvent: event => events.push(event) },
        CustomEvent: class { constructor(type) { this.type = type; } },
        fetch: async (...args) => { requests.push(args); return fetcher(...args); },
    });
    vm.runInContext(source.replace(/^export /gm, ''), context);
    return { send: context.sendRequisition, requests, events };
}
function response(data, status = 200, contentType = 'application/json') {
    return { ok: status < 400, status, headers: { get: () => contentType }, json: async () => data };
}

test('HTML error pages produce an error object instead of a SyntaxError with a success message', async () => {
    const html = response(null, 500, 'text/html');
    html.json = () => { throw new Error('HTML should not be parsed as JSON'); };
    const page = setup(async () => html);
    const result = await page.send('transaction-classifier/delete', 'POST');
    assert.match(result.error, /HTTP 500/);
    assert.equal(result.message, undefined);
    assert.equal(page.requests[0][1].headers.Accept, 'application/json');
});

test('malformed JSON and network errors are returned as explicit errors', async () => {
    const malformed = response(null);
    malformed.json = async () => { throw new SyntaxError('Unexpected token <'); };
    const page = setup(async () => malformed);
    assert.match((await page.send('transaction-classifier/delete', 'POST')).error, /interpretar/);
    const offline = setup(async () => { throw new TypeError('Failed to fetch'); });
    const result = await offline.send('transaction-classifier/delete', 'POST');
    assert.match(result.error, /confirmar/);
    assert.equal(result.message, undefined);
});

test('unsuccessful HTTP or business results never expose a success message', async () => {
    for (const [status, data] of [[500, { message: 'Falha na gravação.' }], [200, { success: false, message: 'Treino recusado.' }]]) {
        const page = setup(async () => response(data, status));
        const result = await page.send('transaction-classifier/delete', 'POST');
        assert.equal(result.error, data.message);
        assert.equal(result.message, undefined);
    }
});

test('successful responses retain their data and investment mutation events', async () => {
    const page = setup(async () => response({ message: 'Concluído.' }));
    assert.equal((await page.send('investments', 'POST')).message, 'Concluído.');
    assert.equal(page.events[0].type, 'investments:mutation');
});
