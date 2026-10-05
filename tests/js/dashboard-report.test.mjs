import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const ROOT = new URL('../../', import.meta.url);

async function importModule(path) {
    const source = await readFile(new URL(path, ROOT), 'utf8');
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

test('relatorio mensal conta investimento com categoria ignorada quando subcategoria esta marcada', () => {
    setSessionData({
        categories: JSON.stringify([{ id: 5, description: 'Aplicação', ignore: true }]),
        subcategories: JSON.stringify([{ id: 54, description: 'Independência Financeira', is_investment: true }]),
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

test('relatorio anual conta investimento com categoria ignorada quando subcategoria esta marcada', () => {
    setSessionData({
        categories: JSON.stringify([{ id: 5, description: 'Aplicação', ignore: true }]),
        subcategories: JSON.stringify([{ id: 54, description: 'Independência Financeira', is_investment: true }]),
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
