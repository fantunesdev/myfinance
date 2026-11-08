import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import vm from 'node:vm';

const source = await readFile(new URL('../../statement/static/js/pages/dashboards-page.js', import.meta.url), 'utf8');
function load() {
    const context = vm.createContext({ document: { getElementById() { return null; } } });
    vm.runInContext(source.replace(/^import .*;\n/gm, '').split("yearSeletct.addEventListener('change'")[0], context);
    vm.runInContext(`dashboardLookups = { categoryById: {}, subcategoryById: {},
        cardById: { 1: { id: 1, description: 'Cache antigo' } },
        accountById: { 2: { id: 2, bank: 3 } }, bankById: { 3: { id: 3, icon: '/media/bank.png' } } };`, context);
    return context;
}

test('dashboard preserva ícone expandido mesmo com cartão antigo no cache', () => {
    const context = load();
    context.transactions = [{ card: { id: 1, description: 'Cartão', icon: '/media/card.png' }, account: 2 }];
    const [transaction] = vm.runInContext('normalizeTransactions(transactions)', context);
    assert.equal(transaction.payment_icon, '/media/card.png');
    assert.equal(transaction.card_name, 'Cartão');
});

test('dashboard resolve banco da conta e cartão do número do cartão', () => {
    const context = load();
    context.transactions = [{ account: 2 }];
    assert.equal(vm.runInContext('normalizeTransactions(transactions)[0].payment_icon', context), '/media/bank.png');
    context.transactions = [{ card_number: { id: 5, card: { id: 1, icon: '/media/number-card.png' } } }];
    assert.equal(vm.runInContext('normalizeTransactions(transactions)[0].payment_icon', context), '/media/number-card.png');
});
