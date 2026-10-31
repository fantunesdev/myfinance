import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import vm from 'node:vm';

const source = await readFile(new URL('../../statement/static/js/pages/investments-dashboard.js', import.meta.url), 'utf8');
const storeSource = await readFile(new URL('../../statement/static/js/data/investments-store.js', import.meta.url), 'utf8');
const storeModule = await import(`data:text/javascript,${encodeURIComponent(storeSource)}`);
const tick = () => new Promise(resolve => setImmediate(resolve));
class Element {
    constructor(tag = 'div') { this.tagName = tag.toUpperCase(); this.dataset = {}; this.children = []; this.events = {}; this.style = {}; this.attributes = {}; this.classes = new Set(); this.classList = { toggle: (name, value) => value ? this.classes.add(name) : this.classes.delete(name) }; }
    addEventListener(name, handler) { (this.events[name] ||= []).push(handler); }
    emit(name, event = {}) { for (const fn of this.events[name] || []) fn({ preventDefault() {}, target: this, ...event }); }
    appendChild(child) { this.children.push(child); child.parentElement = this; return child; }
    contains(element) { return element === this || this.children.some(child => child.contains(element)); }
    replaceChildren(...children) { this.children = children; }
    setAttribute(key, value) { this.attributes[key] = value; }
    getContext() { return { canvas: this }; }
    closest() { return null; }
}
const snapshot = revision => ({ schema_version: 1, user_id: 1, revision, has_default_wallet: true,
    totals: { total: '2000', net_income: '-10', available_to_invest: '100' },
    positions: [
        ['CDB', 'fixed_income', '1000'], ['Ação', 'variable_income', '400'],
        ['Encerrado', 'fixed_income', '0'], ['Caixa', 'currency', '100'],
        ['Bitcoin', 'crypto', '200'], ['Ethereum', 'crypto', '300'],
    ].map(([label, asset_type, value], i) => ({ id: i + 1, label, asset_type, value, quantity: '1', average_purchase_price: asset_type === 'variable_income' ? '21.82' : asset_type === 'crypto' ? '25000.25' : null, broker: label === 'Ethereum' ? 'Outro broker' : 'Broker', asset_type_label: asset_type, url: `/investimentos/${i + 1}/` })),
    brokers: [{ label: 'Ativo', value: '2000' }, { label: 'Inativo', value: '0' }],
    progression_datasets: [{ label: 'Patrimônio', color: 'rgba(139, 0, 0, 1)', names: ['2026-01-01'], values: [1500] }],
    interest_datasets: [{ label: 'Resultado', color: 'rgba(139, 0, 0, 1)', names: ['2026-01-01'], values: [-10] }],
});
function browser(storage = new Map()) {
    const elements = new Map();
    const get = id => { if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); };
    get('investment-dashboard-config').textContent = JSON.stringify({ userId: 1, apiUrl: '/api/investments/dashboard/' });
    get('line-chart').parentElement = new Element();
    const document = new Element(); document.getElementById = get; document.createElement = tag => new Element(tag); document.visibilityState = 'visible';
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

function descendants(element, tag) {
    return element.children.flatMap(child => [ ...(child.tagName === tag ? [child] : []), ...descendants(child, tag) ]);
}
const groups = page => page.get('investment-positions-body').children.filter(element => element.tagName === 'DETAILS');
const group = (page, type) => groups(page).find(element => element.dataset.assetType === type);
const rows = page => descendants(page.get('investment-positions-body'), 'TBODY').flatMap(body => body.children);
const asMoney = value => value.replace(/\s/g, ' ');
function toggle(element, open) { element.open = open; element.emit('toggle'); }

test('positions group only by type with totals and category-specific columns', async () => {
    const page = browser(); await tick();
    assert.equal(page.calls(), 1);
    assert.equal(groups(page).length, 4);
    assert.equal(rows(page).length, 5);
    assert.equal(page.get('investment-brokers-body').children.length, 1);
    const fixed = group(page, 'fixed_income');
    assert.equal(fixed.children[0].children.length, 2);
    assert.equal(fixed.children[0].children[0].textContent, 'Renda fixa');
    assert.equal(asMoney(fixed.children[0].children[1].textContent), 'R$ 1.000,00');
    assert.deepEqual(descendants(fixed, 'TH').map(th => th.textContent), ['Investimento', 'Broker', 'Valor']);
    const variable = group(page, 'variable_income');
    assert.equal(descendants(variable, 'TBODY')[0].children[0].children.length, 5);
    assert.equal(asMoney(descendants(variable, 'TBODY')[0].children[0].children[3].textContent), 'R$ 21,82');
    const crypto = group(page, 'crypto');
    assert.equal(asMoney(crypto.children[0].children[1].textContent), 'R$ 500,00');
    assert.equal(descendants(crypto, 'TBODY')[0].children.length, 2);
    assert.equal(descendants(crypto, 'DETAILS').length, 0);
    assert.equal(groups(page).every(element => !element.open), true);
});

test('chart selection opens only its accordion while every type stays visible', async () => {
    const page = browser(); await tick();
    toggle(group(page, 'crypto'), true);
    toggle(group(page, 'currency'), true);
    page.window.investmentAllocationChart.select(0);
    assert.equal(page.window.investmentChart.config.type, 'bar');
    assert.equal(groups(page).length, 4);
    assert.equal(group(page, 'fixed_income').open, true);
    assert.equal(group(page, 'crypto').open, false);
    assert.equal(group(page, 'currency').open, false);
    assert.equal(rows(page).length, 5);
    assert.equal(page.get('investment-positions-title').textContent, 'Posições');
    assert.match(page.window.location.href, /asset_type=fixed_income/);
    page.get('investment-positions-toggle').emit('click');
    page.get('investment-brokers-toggle').emit('click');
    assert.equal(rows(page).length, 6);
    assert.equal(group(page, 'fixed_income').open, true);
    assert.equal(page.get('investment-brokers-body').children.length, 2);
    page.get('line-chart').parentElement.emit('click');
    assert.equal(page.window.investmentChart.config.type, 'line');
    assert.equal(groups(page).length, 4);
    assert.equal(groups(page).every(element => !element.open), true);
    assert.equal(new URL(page.window.location.href).searchParams.has('asset_type'), false);
    page.window.investmentAllocationChart.select(2);
    assert.equal(groups(page).length, 4);
    assert.equal(group(page, 'crypto').open, true);
    assert.equal(group(page, 'fixed_income').open, false);
    assert.equal(rows(page).length, 6);
    page.window.emit('popstate', { state: { investmentDashboard: { assetType: 'variable_income', showAllPositions: true, showAllBrokers: true, openPositionTypes: ['variable_income'] } } });
    assert.equal(rows(page).length, 6);
    assert.equal(group(page, 'variable_income').open, true);
    assert.equal(group(page, 'crypto').open, false);
    assert.equal(page.calls(), 1);
    const returnVisit = browser(page.storage); await tick();
    assert.equal(returnVisit.calls(), 0);
    assert.equal(groups(returnVisit).length, 4);
    assert.equal(group(returnVisit, 'variable_income').open, true);
    assert.equal(returnVisit.window.investmentChart.config.type, 'bar');
});

test('free areas of either chart collapse groups and restore the overview without requests', async () => {
    const page = browser(); await tick();
    toggle(group(page, 'fixed_income'), true);
    page.get('investment-allocation-container').emit('click');
    assert.equal(groups(page).every(element => !element.open), true);
    page.window.investmentAllocationChart.select(2);
    const chart = page.window.investmentChart;
    chart.getElementsAtEventForMode = () => [{ index: 0 }];
    page.get('line-chart').parentElement.emit('click', { target: page.get('line-chart') });
    assert.equal(group(page, 'crypto').open, true);
    assert.equal(page.window.investmentChart.config.type, 'bar');
    chart.getElementsAtEventForMode = () => [];
    page.get('line-chart').parentElement.emit('click', { target: page.get('line-chart') });
    assert.equal(groups(page).every(element => !element.open), true);
    assert.equal(page.window.investmentChart.config.type, 'line');
    page.window.investmentAllocationChart.select(0);
    page.get('investment-allocation-container').emit('click');
    assert.equal(groups(page).every(element => !element.open), true);
    assert.equal(page.window.investmentChart.config.type, 'line');
    assert.equal(page.calls(), 1);
});

test('multiple accordions retain their state through filters and navigation', async () => {
    const page = browser(); await tick();
    const fixed = group(page, 'fixed_income');
    toggle(fixed, true);
    toggle(group(page, 'crypto'), true);
    assert.equal(group(page, 'crypto').open, true);
    assert.equal(fixed.open, true);
    toggle(fixed, false);
    page.get('investment-positions-toggle').emit('click');
    assert.equal(group(page, 'crypto').open, true);
    assert.equal(group(page, 'fixed_income').open, false);
    // A queued toggle from an obsolete element must not overwrite current state.
    toggle(fixed, true);
    const returnVisit = browser(page.storage); await tick();
    assert.equal(group(returnVisit, 'crypto').open, true);
    assert.equal(group(returnVisit, 'fixed_income').open, false);
    assert.equal(page.calls(), 1);
    assert.equal(returnVisit.calls(), 0);
});

test('notifications preserve accordion state; errors retain data and expired auth clears groups', async () => {
    const page = browser(); await tick();
    page.window.investmentAllocationChart.select(0);
    toggle(group(page, 'fixed_income'), false);
    page.document.visibilityState = 'hidden'; page.change('b');
    page.window.emit('investments:changed', { detail: { revision: 'b' } });
    page.window.emit('investments:changed', { detail: { revision: 'b' } });
    await tick(); assert.equal(page.calls(), 1);
    page.document.visibilityState = 'visible'; page.document.emit('visibilitychange'); await tick();
    assert.equal(page.calls(), 2);
    assert.equal(page.window.investmentChart.config.type, 'bar');
    assert.equal(rows(page).length, 5);
    assert.equal(group(page, 'fixed_income').open, false);
    page.window.emit('investments:changed', { detail: { revision: 'b' } }); await tick();
    assert.equal(page.calls(), 2);
    page.change('c', 500); page.get('investment-refresh').emit('click'); await tick();
    assert.equal(rows(page).length, 5);
    assert.match(page.get('investment-load-status').textContent, /última atualização/);
    page.change('c', 403); page.get('investment-refresh').emit('click'); await tick();
    assert.equal(groups(page).length, 0);
    assert.equal(page.get('investment-total').textContent, '—');
});
