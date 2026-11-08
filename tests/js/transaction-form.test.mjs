import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import vm from 'node:vm';

const source = await readFile(new URL('../../statement/static/js/pages/transaction-form.js', import.meta.url), 'utf8');

function element(value = '') {
    return {
        value,
        options: [],
        listeners: {},
        classList: { add() {}, remove() {} },
        addEventListener(name, handler) { this.listeners[name] = handler; },
    };
}

function loadForm(services = {}, type = element('saida')) {
    const selects = {
        type, category: element('1'), subcategory: element('11'),
        paymentMethod: element('2'), account: element(), card: element(),
        postedDate: element('2026-11-01'), paymentDate: null, value: element('100'),
    };
    selects.category.options = [{ id: 1, description: 'Alimentação' }];
    selects.subcategory.options = [{ id: 11, description: 'Mercado' }];
    const context = {
        selects, services,
        initializeFuelForm() {},
        enhanceSearchableSelect() { return null; },
        buttons: { otherOptions: element() },
        divs: { account: element(), card: element() },
        selectInput: {
            renderOptions(select, options) {
                select.options = Array.from(options);
                select.value = '0';
            },
        },
        document: {
            readyState: 'complete',
            querySelector() { return null; },
            getElementById() { return null; },
        },
    };
    vm.runInNewContext(source.replace(/^import .*;\n/gm, ''), context);
    return selects;
}

function deferred() {
    let resolve;
    const promise = new Promise(done => { resolve = done; });
    return { promise, resolve };
}

test('abrir a edição preserva a categoria e subcategoria renderizadas pelo servidor', () => {
    const selects = loadForm();
    assert.equal(selects.category.value, '1');
    assert.equal(selects.subcategory.value, '11');
});

test('trocar o tipo limpa a seleção anterior e carrega apenas categorias do novo tipo', async () => {
    const request = deferred();
    const selects = loadForm({
        getCategoriesByType(type) {
            assert.equal(type, 'entrada');
            return request.promise;
        },
    });
    selects.type.value = 'entrada';
    const changed = selects.type.listeners.change();
    assert.equal(selects.category.options.length, 0);
    assert.equal(selects.subcategory.options.length, 0);
    request.resolve([{ id: 2, description: 'Receitas' }]);
    await changed;
    assert.deepEqual(selects.category.options, [{ id: 2, description: 'Receitas' }]);
    assert.equal(selects.subcategory.value, '0');
});

test('trocar ou limpar a categoria atualiza as subcategorias mesmo sem campo de tipo', async () => {
    const calls = [];
    const selects = loadForm({
        async getChildrenResource(...args) {
            calls.push(args);
            return [{ id: 22, description: 'Ônibus' }];
        },
    }, null);
    selects.category.value = '2';
    await selects.category.listeners.change();
    assert.deepEqual(calls, [['categories', 'subcategories', '2']]);
    assert.deepEqual(selects.subcategory.options, [{ id: 22, description: 'Ônibus' }]);
    assert.equal(selects.subcategory.value, '0');

    for (const empty of ['', '0']) {
        selects.category.value = empty;
        await selects.category.listeners.change();
        assert.equal(selects.subcategory.options.length, 0);
    }
    assert.equal(calls.length, 1);
});

test('respostas atrasadas não substituem as categorias do tipo selecionado por último', async () => {
    const revenue = deferred();
    const expense = deferred();
    const selects = loadForm({
        getCategoriesByType(type) { return type === 'entrada' ? revenue.promise : expense.promise; },
    });
    selects.type.value = 'entrada';
    const first = selects.type.listeners.change();
    selects.type.value = 'saida';
    const second = selects.type.listeners.change();
    expense.resolve([{ id: 1, description: 'Alimentação' }]);
    await second;
    revenue.resolve([{ id: 2, description: 'Receitas' }]);
    await first;
    assert.deepEqual(selects.category.options, [{ id: 1, description: 'Alimentação' }]);
});

test('respostas atrasadas não substituem as subcategorias da categoria selecionada por último', async () => {
    const firstRequest = deferred();
    const secondRequest = deferred();
    const selects = loadForm({
        getChildrenResource(model, child, id) { return id === '1' ? firstRequest.promise : secondRequest.promise; },
    });
    const first = selects.category.listeners.change();
    selects.category.value = '2';
    const second = selects.category.listeners.change();
    secondRequest.resolve([{ id: 22, description: 'Ônibus' }]);
    await second;
    firstRequest.resolve([{ id: 11, description: 'Mercado' }]);
    await first;
    assert.deepEqual(selects.subcategory.options, [{ id: 22, description: 'Ônibus' }]);
});

test('trocar o tipo descarta respostas de subcategorias da seleção anterior', async () => {
    const request = deferred();
    const selects = loadForm({
        getChildrenResource() { return request.promise; },
        async getCategoriesByType() { return [{ id: 2, description: 'Receitas' }]; },
    });
    const first = selects.category.listeners.change();
    selects.type.value = 'entrada';
    await selects.type.listeners.change();
    request.resolve([{ id: 11, description: 'Mercado' }]);
    await first;
    assert.equal(selects.subcategory.options.length, 0);
});
