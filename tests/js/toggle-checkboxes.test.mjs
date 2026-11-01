import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import { runInNewContext } from 'node:vm';

const source = await readFile(
    new URL('../../statement/static/js/pages/toggle-checkboxes.js', import.meta.url),
    'utf8'
);
const currency = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });

function row(id, value, type = 'saida', cashflow = true) {
    const classes = new Set();
    const attributes = {
        'data-tx-id': String(id),
        'data-value': String(value),
        'data-type': type,
        'data-show-in-cashflow': String(cashflow),
    };
    const checkbox = { checked: false };
    return {
        checkbox,
        classList: {
            contains: name => classes.has(name),
            add: (...names) => names.forEach(name => classes.add(name)),
            remove: (...names) => names.forEach(name => classes.delete(name)),
        },
        getAttribute: name => attributes[name] ?? null,
        setAttribute: (name, value) => { attributes[name] = value; },
        querySelector: () => checkbox,
    };
}

function page(rows, saved = {}) {
    const dashboard = { textContent: '' };
    const mobile = { textContent: '' };
    const storage = new Map(Object.entries(saved));
    const visibilityEvents = [];
    const body = {
        rows,
        querySelector(selector) {
            const id = selector.match(/data-tx-id="([^"]+)"/)?.[1];
            return rows.find(row => row.getAttribute('data-tx-id') === id) ?? null;
        },
        querySelectorAll(selector) {
            if (selector.includes('input')) return rows.map(row => row.checkbox);
            return rows.filter(row => row.classList.contains(selector.slice(3)));
        },
    };
    const table = { tBodies: [body], dataset: { pageKey: '/2026/11/' } };
    const context = {
        window: { dispatchEvent: event => visibilityEvents.push(event) },
        CustomEvent: class {
            constructor(type, options) { this.type = type; this.detail = options.detail; }
        },
        document: {
            addEventListener() {},
            getElementById: () => null,
            createElement: () => ({}),
            body: { appendChild() {} },
            querySelector(selector) {
                if (selector === '.dashboard .expenses b.font-16') return dashboard;
                if (selector === '.mobile-total') return mobile;
                return null;
            },
        },
        localStorage: {
            getItem: key => storage.get(key) ?? null,
            setItem: (key, value) => storage.set(key, value),
            removeItem: key => storage.delete(key),
        },
        requestAnimationFrame() {},
        setTimeout() {},
        console: {
            debug() {},
            error(message, error) { throw error ?? new Error(message); },
        },
    };
    runInNewContext(source, context);
    return {
        ...context,
        table,
        dashboard,
        mobile,
        storage,
        visibilityEvents,
        assertTotals(expenses, total) {
            assert.equal(dashboard.textContent, 'Total de gastos: ' + currency.format(expenses));
            assert.equal(mobile.textContent, 'Total: ' + currency.format(total));
        },
    };
}

test('ocultar uma despesa reduz os gastos sem somar receitas ao dashboard', () => {
    const rows = [row(1, 5000, 'entrada'), row(2, 1000), row(3, 500)];
    const app = page(rows);
    app.recalcDashboardTotals(app.table);
    app.assertTotals(1500, 6500);

    rows[2].checkbox.checked = true;
    app.hideCheckedRows(app.table);

    app.assertTotals(1000, 6000);
    assert.equal(app.visibilityEvents.at(-1).type, 'myfinance:transaction-visibility-changed');
    assert.equal(app.visibilityEvents.at(-1).detail.table, app.table);
    assert.equal(app.storage.get('myfinance:hiddenRows:/2026/11/'), '["3"]');

    app.revealHiddenRows(app.table);
    app.assertTotals(1500, 6500);
    assert.equal(app.storage.has('myfinance:hiddenRows:/2026/11/'), false);
});

test('ocultar uma receita não altera os gastos e recálculos não acumulam valores', () => {
    const rows = [row(1, 5000, 'entrada'), row(2, 1000)];
    const app = page(rows);
    rows[0].checkbox.checked = true;

    for (let attempt = 0; attempt < 3; attempt++) {
        app.hideCheckedRows(app.table);
        app.assertTotals(1000, 1000);
        app.revealHiddenRows(app.table);
        app.assertTotals(1000, 6000);
    }
});

test('subcategorias excluídas do fluxo de caixa continuam fora dos gastos', () => {
    const rows = [row(1, 5000, 'entrada'), row(2, 1000), row(3, 3000, 'saida', false)];
    const app = page(rows);
    app.recalcDashboardTotals(app.table);
    app.assertTotals(1000, 9000);

    rows[2].checkbox.checked = true;
    app.hideCheckedRows(app.table);
    app.assertTotals(1000, 6000);
    app.revealHiddenRows(app.table);
    app.assertTotals(1000, 9000);
});

test('valores decimais e estornos são preservados sem contar linhas de subtotal', () => {
    const subtotal = row(5, 0);
    subtotal.getAttribute = () => null;
    const app = page([
        row(1, '1234.56'),
        row(2, '100,25'),
        row(3, '-34.56'),
        row(4, 5000, 'entrada'),
        subtotal,
        row(6, 'Infinity'),
        row(7, '100invalid'),
    ]);
    app.recalcDashboardTotals(app.table);
    app.assertTotals(1300.25, 6300.25);
});

test('ocultar todas as transações zera os totais', () => {
    const rows = [row(1, 5000, 'entrada'), row(2, 1000)];
    const app = page(rows);
    rows.forEach(row => { row.checkbox.checked = true; });
    app.hideCheckedRows(app.table);
    app.assertTotals(0, 0);
});

test('restaurar transações ocultas mantém os gastos corretos após recarregar', () => {
    const app = page([row(1, 5000, 'entrada'), row(2, 1000), row(3, 500)], {
        'myfinance:hiddenRows:/2026/11/': '["3"]',
    });
    assert.equal(app.loadHiddenRows(app.table), true);
    app.recalcDashboardTotals(app.table);
    app.assertTotals(1000, 6000);
});

test('grupos ocultos restaurados recalculam os gastos e podem ser revelados', () => {
    const app = page([row(1, 5000, 'entrada'), row(2, 1000), row(3, 500)], {
        'myfinance:groups:/2026/11/': '[{"name":"Viagem","ids":["3"]}]',
        'myfinance:hiddenGroups:/2026/11/': '["Viagem"]',
    });
    app.loadGroups(app.table);
    app.assertTotals(1000, 6000);
    app.showGroupByName(app.table, 'Viagem');
    app.assertTotals(1500, 6500);
    app.hideGroupByName(app.table, 'Viagem');
    app.assertTotals(1000, 6000);
});
