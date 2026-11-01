import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import vm from 'node:vm';

const source = (await readFile(new URL('../../statement/static/js/pages/user/classifier-jobs.js', import.meta.url), 'utf8'))
    .replace('export async function startClassifierJob', 'async function startClassifierJob') + '\nglobalThis.start = startClassifierJob;';
const flush = () => new Promise(resolve => setImmediate(resolve));

function setup(fetcher, initial = {}) {
    const events = {}, timers = [], requests = [], modals = [], storage = { ...initial };
    const buttons = Object.fromEntries(['subcategory-train-btn', 'subcategory-feedback-btn', 'description-train-btn', 'description-feedback-btn', 'delete-feedbacks-btn'].map(id => [id, { disabled: false }]));
    const panels = Object.fromEntries(['description', 'subcategory'].map(predictor => {
        const progress = { hidden: false, removeAttribute() { delete this.value; } };
        const text = { textContent: '' };
        return [predictor, { hidden: true, progress, text, querySelector: selector => selector === 'progress' ? progress : text }];
    }));
    const window = { addEventListener: (event, fn) => { events[event] = fn; }, showModal: (...args) => modals.push(args) };
    const document = { cookie: 'csrftoken=csrf-value', getElementById: id => buttons[id], querySelector(selector) {
        if (selector.startsWith('meta')) return { content: '1' };
        if (selector === '[data-classifier-progress]') return panels.description;
        const predictor = selector.includes('subcategory') ? 'subcategory' : 'description';
        return selector.includes('data-classifier-status') ? {} : panels[predictor];
    } };
    const context = vm.createContext({ document, window, console, Date, Map, Set, JSON, Math, AbortController,
        crypto: { randomUUID: () => '12345678-1234-1234-1234-123456789012' },
        sessionStorage: { getItem: key => storage[key] || null, setItem: (key, value) => { storage[key] = value; } },
        fetch: async (url, options) => { requests.push({ url, options }); return fetcher(url, options); },
        setInterval: fn => { const timer = { fn }; timers.push(timer); return timer; }, clearInterval() {},
        setTimeout: () => 1, clearTimeout() {}, decodeURIComponent,
    });
    vm.runInContext(source, context);
    return { events, timers, requests, modals, storage, buttons, panels, start: context.start };
}
const response = (data, status = 200) => ({ ok: status < 400, status, json: async () => data });
const key = 'myfinance:classifier:pending:1';
function job(changes = {}) {
    return { id: '12345678-1234-1234-1234-123456789012', predictor: 'description', operation: 'feedback',
        status: 'running', stage: 'training', revision: 2, completed: 3, total: 10,
        heartbeat_at: new Date().toISOString(), created_at: new Date().toISOString(), ...changes };
}

test('uncertain HTTP acceptance retains identifier and later recovers success without resending feedback', async () => {
    let current = [];
    const page = setup(async (url, options) => {
        if (options?.method === 'POST') throw new Error('lost HTTP response');
        return response({ jobs: current });
    });
    await flush();
    await page.start('transaction-classifier/description/feedback');
    assert.equal(page.buttons['description-feedback-btn'].disabled, true);
    const request = JSON.parse(page.storage[key])[0];
    assert.equal(request.id, page.requests.at(-1).options.headers['Idempotency-Key']);
    assert.equal(page.requests.at(-1).options.headers['X-CSRFToken'], 'csrf-value');
    assert.equal(page.modals.length, 0);
    current = [job({ status: 'succeeded', stage: 'completed', message: 'Concluído com sucesso.' })];
    await page.timers[0].fn();
    assert.equal(page.panels.description.text.textContent, 'Concluído com sucesso.');
    assert.equal(page.panels.description.progress.value, 100);
    assert.equal(page.buttons['description-feedback-btn'].disabled, false);
    assert.equal(JSON.parse(page.storage[key]).length, 0);
    assert.equal(page.requests.filter(request => request.options?.method === 'POST').length, 1);
});

test('lost heartbeat displays uncertainty and old websocket messages cannot regress progress', async () => {
    const page = setup(async () => response({ jobs: [job()] }));
    await flush();
    assert.match(page.panels.description.text.textContent, /3 de 10/);
    page.events['classifier:changed']({ detail: job({ revision: 3, completed: 6, heartbeat_at: new Date(Date.now() - 60000).toISOString() }) });
    assert.match(page.panels.description.text.textContent, /6 de 10/);
    assert.match(page.panels.description.text.textContent, /Sem atualização; verificando/);
    assert.equal(page.buttons['description-feedback-btn'].disabled, true);
    page.events['classifier:changed']({ detail: job({ revision: 2, completed: 1 }) });
    assert.match(page.panels.description.text.textContent, /6 de 10/);
    page.events['classifier:changed']({ detail: job({ revision: 4, status: 'failed', stage: 'failed', message: 'Falha confirmada no disco.' }) });
    assert.equal(page.panels.description.text.textContent, 'Falha confirmada no disco.');
    assert.equal(page.buttons['description-feedback-btn'].disabled, false);
});

test('reload retries uncertain acceptance using the same saved identifier', async () => {
    const request = { id: job().id, predictor: 'description', route: 'transaction-classifier/description/feedback', created_at: new Date().toISOString() };
    const page = setup(async (url, options) => options?.method === 'POST' ? response({ job: job({ status: 'queued' }) }, 202) : response({ jobs: [] }), { [key]: JSON.stringify([request]) });
    await flush();
    const sent = page.requests.find(request => request.options?.method === 'POST');
    assert.equal(sent.options.headers['Idempotency-Key'], request.id);
    assert.equal(JSON.parse(page.storage[key]).length, 0);
});

test('explicit rejection unlocks controls and explains why request was not accepted', async () => {
    const page = setup(async (url, options) => options?.method === 'POST' ? response({ error: 'Nenhum feedback disponível.' }, 400) : response({ jobs: [] }));
    await flush();
    await page.start('transaction-classifier/description/feedback');
    assert.equal(page.buttons['description-feedback-btn'].disabled, false);
    assert.equal(JSON.parse(page.storage[key]).length, 0);
    assert.equal(page.modals[0][1], 'Nenhum feedback disponível.');
});

test('HTML server errors preserve uncertain acceptance and can recover the result later', async () => {
    let current = [];
    const page = setup(async (url, options) => options?.method === 'POST'
        ? { ok: false, status: 500, json: async () => { throw new SyntaxError('Unexpected token <'); } }
        : response({ jobs: current }));
    await flush();
    await page.start('transaction-classifier/description/feedback');
    assert.equal(page.buttons['description-feedback-btn'].disabled, true);
    assert.equal(JSON.parse(page.storage[key]).length, 1);
    assert.equal(page.modals.length, 0);
    current = [job({ status: 'succeeded', stage: 'completed', message: 'Concluído.' })];
    await page.timers[0].fn();
    assert.equal(page.panels.description.text.textContent, 'Concluído.');
    assert.equal(page.buttons['description-feedback-btn'].disabled, false);
});

test('HTML access rejection explains the session problem without exposing a JSON parser error', async () => {
    const page = setup(async (url, options) => options?.method === 'POST'
        ? { ok: false, status: 403, json: async () => { throw new SyntaxError('Unexpected token <'); } }
        : response({ jobs: [] }));
    await flush();
    await page.start('transaction-classifier/description/feedback');
    assert.equal(page.buttons['description-feedback-btn'].disabled, false);
    assert.match(page.modals[0][1], /sessão expirou ou o acesso foi recusado/);
    assert.equal(JSON.parse(page.storage[key]).length, 0);
});
