import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import vm from 'node:vm';

const source = await readFile(new URL('../../statement/static/js/pages/import-transactions.js', import.meta.url), 'utf8');
const eventSource = await readFile(new URL('../../statement/static/js/pages/import-event.js', import.meta.url), 'utf8');
const functions = source.slice(source.indexOf('function getFormData('), source.indexOf('/**\n * Método acessório de importTransactions que cria um novo recurso'));

function setup() {
    const context = vm.createContext({ document: { getElementById: () => ({ value: '1' }) } });
    vm.runInContext(eventSource.replace(/^export /gm, ''), context);
    vm.runInContext(functions, context);
    return context;
}

test('import feedback retains the statement description and bank category after editing', () => {
    const page = setup();
    const original = { description: 'Mercado', original_description: 'GREBOE CIA LTDA ME', source_category: 'SUPERMERCADO', category: 1, subcategory: 10 };
    const feedback = page.buildFeedback(original, { description: 'Alimentação', category: 1, subcategory: 11 });
    assert.equal(feedback.description, 'GREBOE CIA LTDA ME');
    assert.equal(feedback.source_category, 'SUPERMERCADO');
    assert.equal(feedback.corrected_subcategory_id, 11);
});

test('confirmed transaction retains the bank category when submitted', () => {
    const data = setup().getFormData(1, { original_description: 'GREBOE', source_category: 'SUPERMERCADO' });
    assert.equal(data.original_description, 'GREBOE');
    assert.equal(data.source_category, 'SUPERMERCADO');
});

test('imports with no source metadata remain compatible', () => {
    const page = setup();
    const feedback = page.buildFeedback({ description: 'Loja', category: 1, subcategory: 10 }, { description: 'Mercado', category: 1, subcategory: 11 });
    assert.equal(feedback.description, 'Loja');
    assert.equal(feedback.source_category, '');
});


test('unchanged numeric IDs submitted as strings do not create correction feedback', () => {
    const feedback = setup().buildFeedback({ description: 'Mercado', category: 1, subcategory: 10 }, { description: 'Mercado', category: '1', subcategory: '10' });
    assert.equal(feedback, null);
});
