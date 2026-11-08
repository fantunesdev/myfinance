import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import vm from 'node:vm';

const source = await readFile(new URL('../../statement/static/js/data/expenses-table.js', import.meta.url), 'utf8');
const context = vm.createContext({ chartPolicy: {} });
vm.runInContext(source.replace(/^import .*;\n/gm, '').replace(/^export /gm, ''), context);

const transaction = {
    posted_date: '2026-11-08', account: 2, category: 4, subcategory: 5,
    description: 'Posto', value: 230, currency: 'BRL',
};
const resources = {
    accounts: [{ id: 2, bank: 3 }],
    cards: [{ id: 1, icon: '/media/card.png' }],
    banks: [{ id: 3, icon: '/media/bank.png' }],
    category: { id: 4, description: 'Transporte' },
    subcategories: [{ id: 5, name: 'Combustível' }],
};

test('tabela das barras resolve banco por ID ou objeto expandido', () => {
    assert.equal(context.setData(transaction, resources)[1], '/media/bank.png');
    const expanded = { ...resources, accounts: [{ id: 2, bank: { id: 3, icon: '/media/expanded-bank.png' } }] };
    assert.equal(context.setData(transaction, expanded)[1], '/media/expanded-bank.png');
});

test('tabela prioriza cartão e gera exatamente uma coluna de banco/cartão', () => {
    const data = context.setData({ ...transaction, card: 1 }, resources);
    assert.equal(data[1], '/media/card.png');
    assert.equal(data[2], 'Transporte');
    assert.equal(data.length, 6);
});

test('tabela aceita relações expandidas e cartão vindo do número do cartão', () => {
    const expanded = { ...transaction, card: { id: 1, icon: '/media/expanded-card.png' }, subcategory: { id: 5 } };
    assert.equal(context.setData(expanded, resources)[1], '/media/expanded-card.png');
    const numbered = { ...transaction, card_number: { card: 1 } };
    assert.equal(context.setData(numbered, resources)[1], '/media/card.png');
});

test('ausência de ícone ou recursos não desloca categoria e descrição', () => {
    const data = context.setData(transaction, { ...resources, accounts: null, cards: null, banks: null });
    assert.equal(data[1], '');
    assert.equal(data[2], 'Transporte');
    assert.equal(data[3], 'Combustível');
    assert.equal(data[4], 'Posto');
    assert.equal(data.length, 6);
});
