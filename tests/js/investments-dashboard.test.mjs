import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import vm from 'node:vm';

const source = await readFile(new URL('../../statement/static/js/pages/investments-dashboard.js', import.meta.url), 'utf8');
const storeSource = await readFile(new URL('../../statement/static/js/data/investments-store.js', import.meta.url), 'utf8');
const storeModule = await import(`data:text/javascript,${encodeURIComponent(storeSource)}`);
const tick = () => new Promise(resolve => setImmediate(resolve));
class Element {
    constructor() { this.children = []; this.events = {}; this.style = {}; this.attributes = {}; this.classes = new Set(); this.classList = { toggle: (name, value) => value ? this.classes.add(name) : this.classes.delete(name) }; }
    addEventListener(name, handler) { (this.events[name] ||= []).push(handler); }
    emit(name, event = {}) { for (const fn of this.events[name] || []) fn({ preventDefault() {}, target: this, ...event }); }
    appendChild(child) { this.children.push(child); return child; }
    replaceChildren(...children) { this.children = children; }
    setAttribute(key, value) { this.attributes[key] = value; }
    getContext() { return { canvas: this }; }
    closest() { return null; }
}
const snapshot = revision => ({ schema_version: 1, user_id: 1, revision, has_default_wallet: true,
    totals: { total: '1500', net_income: '-10', available_to_invest: '100' },
    positions: [
        ['CDB', 'fixed_income', '1000'], ['Ação', 'variable_income', '400'],
        ['Encerrado', 'fixed_income', '0'], ['Caixa', 'currency', '100'],
    ].map(([label, asset_type, value], i) => ({ id: i + 1, label, asset_type, value, quantity: '1', broker: 'Broker', asset_type_label: asset_type, url: `/investimentos/${i + 1}/` })),
    brokers: [{ label: 'Ativo', value: '1500' }, { label: 'Inativo', value: '0' }],
    progression_datasets: [{ label: 'Patrimônio', color: 'rgba(139, 0, 0, 1)', names: ['2026-01-01'], values: [1500] }],
    interest_datasets: [{ label: 'Resultado', color: 'rgba(139, 0, 0, 1)', names: ['2026-01-01'], values: [-10] }],
});
function browser(storage = new Map()) {
    const elements = new Map();
    const get = id => { if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); };
    get('investment-dashboard-config').textContent = JSON.stringify({ userId: 1, apiUrl: '/api/investments/dashboard/' });
    get('line-chart').parentElement = new Element();
    const document = new Element(); document.getElementById = get; document.createElement = () => new Element(); document.visibilityState = 'visible';
    const window = new Element(); window.location = { href: 'https://test/investimentos/', assign() { throw Error('unexpected navigation'); } };
    window.sessionStorage = { getItem: key => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value), removeItem: key => storage.delete(key) };
    window.history = { state: null, pushState(state, _, url) { this.state = state; window.location.href = String(url); }, replaceState(state, _, url) { this.state = state; window.location.href = String(url); } };
    class Chart {
        constructor(context, config) { this.canvas = context.canvas; this.config = config; }
        destroy() { this.destroyed = true; }
        getElementsAtEventForMode() { return []; }
    }
    let calls = 0, revision = 'a', status = 200;
    const fetcher = async () => { calls++; return { status, ok: status === 200, headers: { get: key => key === 'content-type' ? 'application/json' : revision }, json: async () => snapshot(revision) }; };
    const context = vm.createContext({ window, document, Chart, URL, Intl, console, clearTimeout, setTimeout,
        ...storeModule,
        createInvestmentStore: options => storeModule.createInvestmentStore({ ...options, fetcher }),
        stackedAreaChart: { drawStackedAreaChart: () => new Chart(get('line-chart').getContext(), { type: 'line' }) },
        doughnutChart: { drawDoughnutChart: (data, label, ignored, options) => {
            const chart = new Chart(get(options.canvasId).getContext(), { type: 'doughnut' });
            chart.select = options.onSliceClick; return chart;
        } },
    });
    vm.runInContext(source.replace(/^import .*;\n/gm, ''), context);
    return { get, window, document, storage, calls: () => calls, change: (next, code = 200) => { revision = next; status = code; } };
}

test('chart selection, tables, blank areas and browser history use the same snapshot without requests', async () => {
    const page = browser(); await tick();
    assert.equal(page.calls(), 1);
    assert.equal(page.get('investment-positions-body').children.length, 3);
    assert.equal(page.get('investment-brokers-body').children.length, 1);
    assert.equal(page.get('investment-result-label').textContent, 'Prejuízo');
    assert.ok(page.get('investment-result').classes.has('red'));
    page.window.investmentAllocationChart.select(0);
    assert.equal(page.window.investmentChart.config.type, 'bar');
    assert.equal(page.get('investment-positions-body').children.length, 1);
    assert.match(page.window.location.href, /asset_type=fixed_income/);
    page.get('investment-positions-toggle').emit('click');
    page.get('investment-brokers-toggle').emit('click');
    assert.equal(page.get('investment-positions-body').children.length, 2);
    assert.equal(page.get('investment-brokers-body').children.length, 2);
    page.get('line-chart').parentElement.emit('click');
    assert.equal(page.window.investmentChart.config.type, 'line');
    assert.equal(new URL(page.window.location.href).searchParams.has('asset_type'), false);
    page.window.emit('popstate', { state: { investmentDashboard: { assetType: 'variable_income', showAllPositions: true, showAllBrokers: true } } });
    assert.equal(page.get('investment-positions-body').children.length, 1);
    assert.equal(page.window.investmentChart.config.type, 'bar');
    assert.equal(page.calls(), 1);
    const returnVisit = browser(page.storage); await tick();
    assert.equal(returnVisit.calls(), 0);
    assert.equal(returnVisit.window.investmentChart.config.type, 'bar');
});

test('notifications defer while hidden, refresh once on return and preserve selection on errors', async () => {
    const page = browser(); await tick();
    page.window.investmentAllocationChart.select(0);
    page.document.visibilityState = 'hidden'; page.change('b');
    page.window.emit('investments:changed', { detail: { revision: 'b' } });
    page.window.emit('investments:changed', { detail: { revision: 'b' } });
    await tick(); assert.equal(page.calls(), 1);
    page.document.visibilityState = 'visible'; page.document.emit('visibilitychange'); await tick();
    assert.equal(page.calls(), 2);
    assert.equal(page.window.investmentChart.config.type, 'bar');
    assert.equal(page.get('investment-positions-body').children.length, 1);
    page.window.emit('investments:changed', { detail: { revision: 'b' } }); await tick();
    assert.equal(page.calls(), 2);
    page.change('c', 500); page.get('investment-refresh').emit('click'); await tick();
    assert.equal(page.get('investment-positions-body').children.length, 1);
    assert.match(page.get('investment-load-status').textContent, /última atualização/);
    page.change('c', 403); page.get('investment-refresh').emit('click'); await tick();
    assert.equal(page.get('investment-positions-body').children.length, 0);
    assert.equal(page.get('investment-total').textContent, '—');
});
