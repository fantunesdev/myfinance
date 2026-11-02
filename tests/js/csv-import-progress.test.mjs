import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import vm from 'node:vm';

const source = await readFile(new URL('../../statement/static/js/pages/import-transactions.js', import.meta.url), 'utf8');
const activitySource = source.slice(source.indexOf('const importProgress ='), source.indexOf('const targetModels ='));
const sendSource = source.slice(source.indexOf('async function sendFile()'), source.indexOf('/**\n * Método principal'));
const flush = () => new Promise(resolve => setImmediate(resolve));

function setup(importer, renderer = async () => {}) {
    const element = (extra = {}) => ({
        disabled: false, value: '', hidden: false,
        setAttribute(name, value) { this[name] = value; },
        removeAttribute(name) { delete this[name]; },
        classList: { add() {}, remove() {} }, ...extra,
    });
    const button = element({ value: 'Importar CSV configurável' });
    const config = element();
    const alreadyDisabled = element({ disabled: true });
    const progress = element();
    const message = element();
    const spinner = element();
    const panel = element({ hidden: true, querySelector: selector => ({
        progress, '[data-import-message]': message, '[data-import-activity]': spinner,
    })[selector] });
    const error = element();
    const timers = new Set();
    let now = 0;
    let calls = 0;
    const context = vm.createContext({
        document: {
            querySelector: selector => selector === '#csv-import-progress' ? panel : error,
            querySelectorAll: () => [button, config, alreadyDisabled],
        },
        importBtn: button, fileInput: { files: ['csv'] },
        selects: { account: { value: '1' }, card: { value: '' }, paymentMethod: { value: '2' } },
        dateColumnInput: { value: 'data' }, descriptionColumnInput: { value: 'descricao' }, valueColumnInput: { value: 'valor' },
        installmentColumnInput: null, installmentFormatInput: null,
        getSelectedCSVImportConfig: () => ({ id: 1, matching_fields: [] }),
        getTargetModel: () => 'statement', targetModels: { statement: 'statement' },
        FormData: class { append() {} }, alert() {}, window: {},
        boxTransactions: element(), renderBox: renderer,
        Date: { now: () => now },
        services: { importTransactions: async () => { calls++; return importer(); } },
        setInterval: fn => { timers.add(fn); return fn; }, clearInterval: fn => timers.delete(fn),
    });
    vm.runInContext(activitySource + sendSource, context);
    return { context, button, config, alreadyDisabled, progress, message, spinner, panel, error, timers,
        calls: () => calls, tick: () => { now += 1000; for (const fn of timers) fn(); } };
}

test('CSV stays locked through the request and asynchronous preview; duplicate clicks are ignored', async () => {
    let respond, finishRender;
    const page = setup(() => new Promise(resolve => { respond = resolve; }), async (rows, update) => {
        update(1, rows.length);
        await new Promise(resolve => { finishRender = resolve; });
    });
    const pending = page.context.sendFile();
    assert.equal(page.button.disabled, true);
    assert.equal(page.config.disabled, true);
    assert.equal(page.panel.hidden, false);
    assert.equal(page.progress.value, undefined);
    assert.match(page.message.textContent, /aguardando processamento/);
    page.tick();
    assert.match(page.message.textContent, /1s decorridos/);
    await page.context.sendFile();
    assert.equal(page.calls(), 1);
    respond([{ id: 1 }, { id: 2 }]);
    await flush();
    assert.equal(page.button.disabled, true);
    assert.equal(page.progress.value, 50);
    assert.equal(page.spinner.hidden, false);
    assert.match(page.message.textContent, /1 de 2/);
    finishRender();
    await pending;
    assert.equal(page.button.disabled, false);
    assert.equal(page.config.disabled, false);
    assert.equal(page.alreadyDisabled.disabled, true);
    assert.equal(page.progress.value, 100);
    assert.equal(page.spinner.hidden, true);
    assert.equal(page.timers.size, 0);
    assert.match(page.message.textContent, /2 lançamento/);
    assert.equal(page.context.window.myFinance.importedTransactions.length, 2);
});

for (const [label, importer, renderer, expected] of [
    ['API validation', () => ({ errors: 'Coluna ausente' }), undefined, 'Coluna ausente'],
    ['network failure returned by services', () => new Error('Sem conexão'), undefined, 'Sem conexão'],
    ['rejected request', () => { throw new Error('Falha de rede'); }, undefined, 'Falha de rede'],
    ['preview failure', () => [], async () => { throw new Error('Falha nas categorias'); }, 'Falha nas categorias'],
]) {
    test(`${label} clears activity, unlocks the form and allows retry`, async () => {
        const page = setup(importer, renderer);
        await page.context.sendFile();
        assert.equal(page.button.disabled, false);
        assert.equal(page.button.value, 'Importar CSV configurável');
        assert.equal(page.error.textContent, expected);
        assert.equal(page.progress.hidden, true);
        assert.equal(page.spinner.hidden, true);
        assert.equal(page.timers.size, 0);
        await page.context.sendFile();
        assert.equal(page.calls(), 2);
    });
}

test('missing file does not start a request or activity indicator', async () => {
    const page = setup(() => []);
    page.context.fileInput.files = [];
    await page.context.sendFile();
    assert.equal(page.calls(), 0);
    assert.equal(page.panel.hidden, true);
    assert.equal(page.button.disabled, false);
    assert.equal(page.timers.size, 0);
});
