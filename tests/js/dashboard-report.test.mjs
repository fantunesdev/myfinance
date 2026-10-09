import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const ROOT = new URL('../../', import.meta.url);

async function importModule(path) {
    let source = await readFile(new URL(path, ROOT), 'utf8');

    if (source.includes("import * as chartPolicy from './chart-policy.js';")) {
        const chartPolicySource = await readFile(
            new URL('statement/static/js/data/chart-policy.js', ROOT),
            'utf8'
        );
        const chartPolicyUrl = `data:text/javascript;charset=utf-8,${encodeURIComponent(chartPolicySource)}`;
        source = source.replace(
            "import * as chartPolicy from './chart-policy.js';",
            `const chartPolicy = await import(${JSON.stringify(chartPolicyUrl)});`
        );
    }

    source = source.replace("import * as services from './services.js';", 'const services = {};');

    return import(`data:text/javascript;charset=utf-8,${encodeURIComponent(source)}`);
}

function setSessionData(data) {
    globalThis.sessionStorage = {
        getItem(key) {
            return Object.prototype.hasOwnProperty.call(data, key) ? data[key] : null;
        },
    };
}

const monthsReport = await importModule('statement/static/js/data/months-report.js');
const annualReport = await importModule('statement/static/js/data/annual-report.js');
const categoriesReport = await importModule('statement/static/js/data/categories-report.js');

test('relatorio mensal separa investimento quando demonstrativo anual esta ativo', () => {
    setSessionData({
        subcategories: JSON.stringify([
            {
                id: 54,
                description: 'Independência Financeira',
                is_investment: true,
                show_in_annual_statement: true,
            },
        ]),
    });

    const report = monthsReport.setMontlyReport([
        {
            type: 'saida',
            value: 395.12,
            payment_date: '2026-01-31',
            category: 5,
            subcategory: 54,
            home_screen: true,
        },
    ]);

    assert.equal(report.investments.january, 395.12);
    assert.equal(report.expenses.january, 0);
});

test('relatorio anual separa investimento quando demonstrativo anual esta ativo', () => {
    setSessionData({
        subcategories: JSON.stringify([
            {
                id: 54,
                description: 'Independência Financeira',
                is_investment: true,
                show_in_annual_statement: true,
            },
        ]),
    });

    const report = annualReport.setAnnualReport([
        {
            type: 'saida',
            value: 395.12,
            payment_date: '2026-01-31',
            category: 5,
            subcategory: 54,
            home_screen: true,
        },
    ]);

    assert.equal(report.investments[2026], 395.12);
    assert.equal(report.expenses[2026], 0);
});

test('donut mensal conta investimento como saida quando flag esta ativa', () => {
    setSessionData({
        subcategories: JSON.stringify([
            {
                id: 54,
                description: 'Independência Financeira',
                is_investment: true,
                show_in_monthly_cashflow_donut: true,
            },
        ]),
    });

    const report = categoriesReport.setCategoriesReport(
        [
            {
                type: 'saida',
                value: 395.12,
                payment_date: '2026-01-31',
                category: 5,
                subcategory: 54,
                home_screen: true,
            },
        ],
        [{ id: 5, description: 'Aplicação', type: 'saida' }]
    );

    assert.equal(report.amount.expenses, 395.12);
});

test('barra mensal ignora investimento quando flag esta inativa', () => {
    setSessionData({
        subcategories: JSON.stringify([
            {
                id: 54,
                description: 'Independência Financeira',
                is_investment: true,
                show_in_monthly_cashflow_donut: true,
                show_in_monthly_expense_category_bar: false,
            },
        ]),
    });

    const report = categoriesReport.setCategoriesReport(
        [
            {
                type: 'saida',
                value: 395.12,
                payment_date: '2026-01-31',
                category: 5,
                subcategory: 54,
                home_screen: true,
            },
        ],
        [{ id: 5, description: 'Aplicação', type: 'saida' }]
    );

    assert.equal(report.amount.expenses, 395.12);
    assert.equal(report.expenses[0].amount, 0);
});

test('barra anual ignora investimento quando flag anual esta inativa', () => {
    setSessionData({
        subcategories: JSON.stringify([
            {
                id: 54,
                description: 'Independência Financeira',
                is_investment: true,
                show_in_monthly_cashflow_donut: true,
                show_in_monthly_expense_category_bar: true,
                show_in_annual_expense_category_bar: false,
            },
        ]),
    });

    const report = categoriesReport.setCategoriesReport(
        [
            {
                type: 'saida',
                value: 395.12,
                payment_date: '2026-01-31',
                category: 5,
                subcategory: 54,
                home_screen: true,
            },
        ],
        [{ id: 5, description: 'Aplicação', type: 'saida' }],
        { expenseCategoryBar: 'annual' }
    );

    assert.equal(report.amount.expenses, 395.12);
    assert.equal(report.expenses[0].amount, 0);
});
