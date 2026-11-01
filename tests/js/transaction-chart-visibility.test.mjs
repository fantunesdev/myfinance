import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import vm from 'node:vm';

const ROOT = new URL('../../statement/static/js/', import.meta.url);
const read = path => readFile(new URL(path, ROOT), 'utf8');
const [pageSource, toggleSource, policySource, categorySource, subcategorySource, graphicsSource, tableSource] =
    await Promise.all([
        read('pages/get-transactions.js'), read('pages/toggle-checkboxes.js'), read('data/chart-policy.js'),
        read('data/categories-report.js'), read('data/subcategory-expenses.js'),
        read('layout/elements/graphics.js'), read('data/expenses-table.js'),
    ]);
const withoutImports = source => source.replace(/^import .*;\n/gm, '').replace(/^export /gm, '');

class Element {
    constructor() {
        this.events = {};
        this.style = {};
        const classes = new Set();
        this.classList = {
            add: (...names) => names.forEach(name => classes.add(name)),
            remove: (...names) => names.forEach(name => classes.delete(name)),
            contains: name => classes.has(name),
        };
    }
    addEventListener(name, handler) { (this.events[name] ||= []).push(handler); }
    setAttribute() {}
    appendChild() {}
    getContext() { return { canvas: this }; }
}

const transactions = [
    { id: 1, type: 'entrada', category: 99, subcategory: 990, value: 5000 },
    { id: 2, type: 'saida', category: 10, subcategory: 101, value: 100 },
    { id: 3, type: 'saida', category: 10, subcategory: 102, value: 50 },
    { id: 4, type: 'saida', category: 20, subcategory: 201, value: 200 },
    { id: 5, type: 'saida', category: 30, subcategory: 301, value: 300,
        subcategory_show_in_monthly_expense_category_bar: false },
].map(transaction => ({ ...transaction, posted_date: '2026-11-02', payment_date: '2026-11-02' }));
const categories = [
    { id: 99, type: 'entrada', description: 'Salário' },
    { id: 10, type: 'saida', description: 'Alimentação' },
    { id: 20, type: 'saida', description: 'Transporte' },
    { id: 30, type: 'saida', description: 'Aplicação' },
];
const subcategories = [
    { id: 101, category: 10, description: 'Mercado' },
    { id: 102, category: 10, description: 'Lanches' },
    { id: 201, category: 20, description: 'Ônibus' },
    { id: 301, category: 30, description: 'Aporte', show_in_monthly_expense_category_bar: false },
];

function browser({ hidden = [], hiddenGroup = false, loading = false } = {}) {
    const storage = new Map(Object.entries({
        transactions: JSON.stringify(transactions), categories: JSON.stringify(categories),
        subcategories: JSON.stringify(subcategories), accounts: '[]', cards: '[]', banks: '[]',
        'myfinance:hiddenRows:/2026/11/': JSON.stringify(hidden.map(String)),
        'myfinance:groups:/2026/11/': '[{"name":"Viagem","ids":["2","4"]}]',
        'myfinance:hiddenGroups:/2026/11/': JSON.stringify(hiddenGroup ? ['Viagem'] : []),
    }));
    const elements = new Map();
    const get = id => {
        if (id === 'toggle-checkboxes') return null;
        if (id === 'subcategory-table') return elements.get(id) ?? null;
        if (!elements.has(id)) elements.set(id, new Element());
        return elements.get(id);
    };
    const rows = transactions.map(transaction => {
        const row = new Element();
        row.checkbox = { checked: false };
        const attrs = { 'data-tx-id': String(transaction.id), 'data-value': String(transaction.value),
            'data-type': transaction.type, 'data-show-in-cashflow': 'true' };
        row.getAttribute = name => attrs[name] ?? null;
        row.setAttribute = (name, value) => { attrs[name] = value; };
        row.querySelector = () => row.checkbox;
        return row;
    });
    const table = get('statement-table');
    table.dataset = { pageKey: '/2026/11/' };
    table.querySelectorAll = () => rows.filter(row => row.classList.contains('row-hidden'));
    table.tBodies = [{
        rows,
        querySelector: selector => rows.find(row => row.getAttribute('data-tx-id') === selector.match(/data-tx-id="([^"]+)"/)?.[1]),
        querySelectorAll: selector => selector.includes('input') ? rows.map(row => row.checkbox)
            : rows.filter(row => row.classList.contains(selector.slice(3))),
    }];
    const pending = [];
    const charts = [];
    let fetches = 0;
    let finishLoading;
    let deferSubcategories = false;
    const subcategoryRequests = [];
    let renderedTransactions = [];
    const window = new Element();
    window.location = { pathname: '/relatorio_financeiro/2026/11/' };
    window.dispatchEvent = event => {
        for (const handler of window.events[event.type] || []) pending.push(Promise.resolve(handler(event)));
    };
    const document = new Element();
    document.getElementById = get;
    document.querySelector = selector => selector === '#reset-dashboard-button' ? get('reset-dashboard-button') : null;
    document.createElement = () => new Element();
    document.body = new Element();
    const context = vm.createContext({
        window, document, Intl,
        sessionStorage: { getItem: key => storage.get(key) ?? null,
            setItem: (key, value) => storage.set(key, String(value)), removeItem: key => storage.delete(key) },
        localStorage: { getItem: key => storage.get(key) ?? null,
            setItem: (key, value) => storage.set(key, value), removeItem: key => storage.delete(key) },
        CustomEvent: class { constructor(type, options) { this.type = type; this.detail = options.detail; } },
        requestAnimationFrame() {}, setTimeout() {},
        console: { debug() {}, error(message, error) { throw error ?? new Error(message); } },
        Chart: class {
            constructor(canvas, config) { this.data = config.data; this.options = config.options; charts.push(this); }
            update() { this.updates = (this.updates || 0) + 1; }
            destroy() {}
        },
        originalTable: table, statementBox: get('statement-box'),
        services: {
            async getTransactionsByYearAndMonth() {
                fetches++;
                if (loading) await new Promise(resolve => { finishLoading = resolve; });
                return JSON.parse(storage.get('transactions'));
            },
            async getResource(model) { return JSON.parse(storage.get(model) ?? 'null'); },
            async getChildrenResource(model, child, id) {
                if (deferSubcategories) await new Promise(resolve => subcategoryRequests.push(resolve));
                return subcategories.filter(subcategory => subcategory.category === id);
            },
        },
        tables: { renderTable(father, selected) {
            renderedTransactions = selected;
            const element = new Element();
            element.parentNode = { removeChild: () => elements.delete('subcategory-table') };
            elements.set('subcategory-table', element);
        } },
    });
    function load(source, names) {
        return vm.runInContext(`(() => { ${withoutImports(source)}; return { ${names.join(',')} }; })()`, context);
    }
    context.chartPolicy = load(policySource, ['showInMonthlyCashflowDonut', 'showInMonthlyExpenseCategoryBar', 'showInMonthlyExpenseLine']);
    context.categoryData = load(categorySource, ['getMonthYear', 'setCategoriesReport', 'setCategoriesDataset', 'setAmountDataset']);
    context.subcategoryData = load(subcategorySource, ['setSubcategoryDataset']);
    context.dataTable = load(tableSource, ['orderExpensesBySubcategory']);
    context.graphics = load(graphicsSource, ['drawBarChart', 'drawDoughnutChart', 'updateChart']);
    vm.runInContext(toggleSource, context);
    context.loadHiddenRows(table);
    context.loadGroups(table);
    let controller;
    const ready = vm.runInContext(`(async () => { ${withoutImports(pageSource)}
        return { updateBarChart, setMonthlyExpensesChartMode }; })()`, context).then(result => {
        controller = result;
        context.updateBarChart = result.updateBarChart;
    });
    return {
        ready, storage, charts,
        fetches: () => fetches,
        renderedIds: () => Array.from(renderedTransactions, transaction => transaction.id),
        bars: () => Object.fromEntries(charts[0].data.labels.map((label, i) => [label, charts[0].data.datasets[0].data[i]])),
        hide(ids) {
            rows.forEach(row => { row.checkbox.checked = ids.includes(Number(row.getAttribute('data-tx-id'))); });
            context.hideCheckedRows(table);
        },
        reveal: () => context.revealHiddenRows(table),
        hideGroup: () => context.hideGroupByName(table, 'Viagem'),
        showGroup: () => context.showGroupByName(table, 'Viagem'),
        reset: () => get('reset-dashboard-button').events.click[0](),
        async selectCategory(label) {
            storage.set('bar_label_clicked', label);
            storage.set('bar_chart_level', 'subcategories');
            await controller.updateBarChart(charts[0]);
        },
        async settle() { while (pending.length) await Promise.all(pending.splice(0)); },
        finishLoading: () => finishLoading(),
        deferSubcategories: () => { deferSubcategories = true; },
        resolveSubcategory: index => subcategoryRequests[index](),
        line: () => controller.setMonthlyExpensesChartMode('line'),
    };
}

test('barras acompanham ocultação e revelação sem alterar o cache completo', async () => {
    const app = browser(); await app.ready;
    assert.deepEqual(app.bars(), { Transporte: 200, Alimentação: 150 });
    app.hide([2]); await app.settle();
    assert.deepEqual(app.bars(), { Transporte: 200, Alimentação: 50 });
    app.reveal(); await app.settle();
    assert.deepEqual(app.bars(), { Transporte: 200, Alimentação: 150 });
    assert.equal(app.fetches(), 1);
    assert.deepEqual(JSON.parse(app.storage.get('transactions')), transactions);
});

test('ocultar categoria inteira remove a barra e reset preserva a ocultação', async () => {
    const app = browser(); await app.ready;
    app.hide([2, 3]); await app.settle();
    assert.deepEqual(app.bars(), { Transporte: 200 });
    await app.reset();
    assert.deepEqual(app.bars(), { Transporte: 200 });
    app.hide([4, 5]); await app.settle();
    assert.deepEqual(app.bars(), {});
    assert.equal(app.charts[0].data.datasets[0].backgroundColor.length, 0);
    app.reveal(); await app.settle();
    assert.deepEqual(app.bars(), { Transporte: 200, Alimentação: 150 });
});

test('primeiro desenho respeita transações e grupos ocultos persistidos', async () => {
    const app = browser({ hidden: [3], hiddenGroup: true }); await app.ready;
    assert.deepEqual(app.bars(), {});
    app.showGroup(); await app.settle();
    assert.deepEqual(app.bars(), { Transporte: 200, Alimentação: 100 });
    app.hideGroup(); await app.settle();
    assert.deepEqual(app.bars(), {});
});

test('subcategorias e tabela detalhada usam apenas transações visíveis', async () => {
    const app = browser(); await app.ready;
    await app.selectCategory('Alimentação');
    assert.deepEqual(app.bars(), { Mercado: 100, Lanches: 50 });
    app.hide([2]); await app.settle();
    assert.deepEqual(app.bars(), { Lanches: 50 });
    assert.deepEqual(app.renderedIds(), [3]);
    assert.equal(app.storage.get('bar_label_clicked'), 'Alimentação');
    app.reveal(); await app.settle();
    assert.deepEqual(app.bars(), { Mercado: 100, Lanches: 50 });
});

test('ocultação durante a busca inicial é aplicada quando o gráfico fica pronto', async () => {
    const app = browser({ loading: true });
    await new Promise(resolve => setImmediate(resolve));
    app.hide([4]);
    app.finishLoading(); await app.ready; await app.settle();
    assert.deepEqual(app.bars(), { Alimentação: 150 });
});

test('resposta antiga de subcategorias não sobrescreve uma revelação mais recente', async () => {
    const app = browser(); await app.ready;
    await app.selectCategory('Alimentação');
    app.deferSubcategories();
    app.hide([2]);
    app.reveal();
    app.resolveSubcategory(1);
    await new Promise(resolve => setImmediate(resolve));
    app.resolveSubcategory(0); await app.settle();
    assert.deepEqual(app.bars(), { Mercado: 100, Lanches: 50 });
    assert.deepEqual(app.renderedIds(), [2, 3]);
});

test('alternar para linhas mantém a mesma visibilidade das despesas', async () => {
    const app = browser(); await app.ready;
    await app.line();
    assert.equal(app.charts.at(-1).data.datasets[0].data.at(-1), 650);
    app.hide([2]); await app.settle();
    assert.equal(app.charts.at(-1).data.datasets[0].data.at(-1), 550);
    app.reveal(); await app.settle();
    assert.equal(app.charts.at(-1).data.datasets[0].data.at(-1), 650);
});
