import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import vm from 'node:vm';

const source = await readFile(new URL('../../statement/static/js/pages/investment-application.js', import.meta.url), 'utf8');
const destinations = {
    1: { asset_type: 'fixed_income', due_date: '2027-01-01' },
    2: { asset_type: 'variable_income', due_date: '' },
    3: { asset_type: 'crypto', due_date: '' },
    4: { asset_type: 'fixed_income', due_date: '2028-01-01' },
};
function element(value = '') {
    return { value, id: '', options: [], children: [], textContent: '', required: true, hidden: false, events: {}, attributes: {},
        addEventListener(name, handler) { (this.events[name] ||= []).push(handler); },
        emit(name, event = {}) { const data = { preventDefault() { this.defaultPrevented = true; }, ...event }; for (const handler of this.events[name] || []) handler(data); return data; },
        dispatchEvent(event) { this.emit(event.type, event); },
        cloneNode() { const clone = element(this.value); clone.textContent = this.textContent; return clone; },
        replaceChildren(...children) { this.options = children; this.children = children; },
        appendChild(child) { this.children.push(child); },
        setAttribute(name, value) { this.attributes[name] = value; },
        removeAttribute(name) { delete this.attributes[name]; },
        setCustomValidity(message) { this.validationMessage = message; },
        focus() { this.emit('focus'); },
        contains(child) { return child === this || this.children.some(node => node.contains(child)); },
    };
}
function form(selected = '', type = destinations[selected]?.asset_type || '') {
    const elements = new Map();
    const get = id => { if (!elements.has(id)) { const node = element(); node.id = id; elements.set(id, node); } return elements.get(id); };
    get('investment-destination-options').textContent = JSON.stringify(destinations);
    get('id_asset_type').value = type;
    const names = { 1: 'CDB DI', 2: 'Ações Vale (VALE3)', 3: 'Bitcoin (BTC)', 4: 'Tesouro Pré-fixado' };
    get('id_investment').options = ['', '1', '2', '3', '4'].map(value => { const option = element(value); option.textContent = names[value] || 'Selecione'; return option; });
    get('id_investment').value = selected;
    get('id_quantity').value = '2';
    get('id_unit_price').value = '125';
    get('id_due_date').value = '2027-05-01';
    get('id_amount').value = '250';
    get('investment-destination-picker').children = [get('id_investment'), get('investment-destination-search'), get('investment-destination-results')];
    vm.runInNewContext(source, {
        document: { getElementById: get, createElement: () => element() },
        Event: class { constructor(type, options) { this.type = type; Object.assign(this, options); } },
    });
    return { get,
        type(value) { get('id_asset_type').value = value; get('id_asset_type').emit('change'); },
        select(value) { get('id_investment').value = value; get('id_investment').emit('change'); },
        search(value) { get('investment-destination-search').value = value; get('investment-destination-search').emit('input'); },
        key(key) { return get('investment-destination-search').emit('keydown', { key }); },
    };
}

test('type restricts destinations locally and destination controls units and due date', () => {
    const page = form();
    assert.equal(page.get('id_investment').disabled, true);
    assert.equal(page.get('investment-application-field-quantity').hidden, true);
    assert.equal(page.get('id_quantity').disabled, true);
    page.type('fixed_income');
    assert.equal(page.get('id_investment').options.map(option => option.value).join(','), ',1,4');
    assert.equal(page.get('id_investment').disabled, false);
    page.select('1');
    assert.equal(page.get('id_due_date').value, '2027-01-01');
    assert.equal(page.get('id_quantity').disabled, true);
    page.type('variable_income');
    assert.equal(page.get('id_investment').value, '');
    assert.equal(page.get('id_investment').options.map(option => option.value).join(','), ',2');
    page.select('2');
    assert.equal(page.get('investment-application-field-quantity').hidden, false);
    assert.equal(page.get('id_quantity').disabled, false);
    assert.equal(page.get('id_unit_price').disabled, false);
    assert.equal(page.get('id_due_date').value, '');
    assert.equal(page.get('id_amount').value, '250');
});

test('invalid submissions retain matching selection and units; switching type clears stale data', () => {
    const page = form('2');
    assert.equal(page.get('id_investment').value, '2');
    assert.equal(page.get('id_quantity').value, '2');
    assert.equal(page.get('id_unit_price').value, '125');
    assert.equal(page.get('id_due_date').value, '2027-05-01');
    page.type('crypto');
    assert.equal(page.get('id_investment').value, '');
    assert.equal(page.get('id_quantity').value, '');
    assert.equal(page.get('id_unit_price').value, '');
    page.select('3');
    page.type('fixed_income');
    assert.equal(page.get('investment-application-field-unit_price').hidden, true);
    assert.equal(page.get('id_unit_price').disabled, true);
    assert.equal(page.get('id_investment').options.map(option => option.value).join(','), ',1,4');
});

test('mismatched destinations and empty type cannot retain a stale selection', () => {
    const page = form('2', 'fixed_income');
    assert.equal(page.get('id_investment').value, '');
    assert.equal(page.get('id_quantity').disabled, true);
    page.type('');
    assert.equal(page.get('id_investment').disabled, true);
    assert.equal(page.get('id_investment').options.length, 1);
});

test('search filters names without accents, stays within type and commits only a listed option', () => {
    const page = form();
    assert.equal(page.get('investment-destination-search').disabled, true);
    page.type('fixed_income');
    assert.equal(page.get('investment-destination-search').disabled, false);
    page.search('pre');
    const list = page.get('investment-destination-results');
    assert.equal(list.children.length, 1);
    assert.equal(list.children[0].textContent, 'Tesouro Pré-fixado');
    assert.equal(page.get('id_investment').value, '');
    assert.ok(page.get('investment-destination-search').validationMessage);
    const enter = page.key('Enter');
    assert.equal(enter.defaultPrevented, true);
    assert.equal(page.get('id_investment').value, '4');
    assert.equal(page.get('investment-destination-search').value, 'Tesouro Pré-fixado');
    assert.equal(page.get('investment-destination-search').validationMessage, '');
    assert.equal(page.get('id_due_date').value, '2028-01-01');
    assert.equal(list.hidden, true);
    page.search('VALE3');
    assert.equal(list.children[0].textContent, 'Nenhum investimento encontrado.');
    assert.equal(page.get('id_investment').value, '');
    assert.equal(page.get('id_amount').value, '250');
});

test('keyboard navigation and clicking results select destinations without submitting', () => {
    const page = form();
    page.type('fixed_income');
    assert.equal(page.key('ArrowDown').defaultPrevented, true);
    page.key('ArrowDown');
    page.key('Enter');
    assert.equal(page.get('id_investment').value, '4');
    page.search('CDB');
    page.get('investment-destination-results').children[0].emit('click');
    assert.equal(page.get('id_investment').value, '1');
    assert.equal(page.get('investment-destination-search').value, 'CDB DI');
    assert.equal(page.get('id_due_date').value, '2027-01-01');
    assert.equal(page.get('investment-destination-results').hidden, true);
});

test('unconfirmed search cannot reuse a stale target; Escape explicitly restores it', () => {
    const page = form('2');
    page.search('inexistente');
    page.get('investment-destination-picker').emit('focusout', { relatedTarget: page.get('id_amount') });
    assert.equal(page.get('investment-destination-results').hidden, true);
    assert.equal(page.get('id_investment').value, '');
    assert.ok(page.get('investment-destination-search').validationMessage);
    page.key('Escape');
    assert.equal(page.get('id_investment').value, '2');
    assert.equal(page.get('investment-destination-search').value, 'Ações Vale (VALE3)');
    assert.equal(page.get('id_quantity').value, '2');
    assert.equal(page.get('investment-destination-search').validationMessage, '');
    page.type('crypto');
    assert.equal(page.get('investment-destination-search').value, '');
    assert.equal(page.get('id_investment').value, '');
});

test('amount and quantity calculate unit price using comma decimals without changing the amount', () => {
    const page = form('2');
    page.get('id_amount').value = '2615,46';
    page.get('id_quantity').value = '200';
    page.get('id_quantity').emit('input');
    assert.equal(page.get('id_unit_price').value, '13.0773');
    assert.equal(page.get('id_amount').value, '2615,46');
    page.get('id_amount').value = '2000';
    page.get('id_amount').emit('input');
    assert.equal(page.get('id_unit_price').value, '10');
    page.get('id_quantity').value = '100';
    page.get('id_quantity').emit('input');
    assert.equal(page.get('id_unit_price').value, '20');
});

test('fractional quantities, grouping separators and six-decimal precision are supported', () => {
    const page = form('3');
    page.get('id_amount').value = '1.234,56';
    page.get('id_quantity').value = '0,002';
    page.get('id_quantity').emit('input');
    assert.equal(page.get('id_unit_price').value, '617280');
    page.get('id_amount').value = '100';
    page.get('id_quantity').value = '3';
    page.get('id_amount').emit('input');
    assert.equal(page.get('id_unit_price').value, '33.333333');
});

test('missing, nonpositive or invalid values clear stale price; fixed income stays without unit price', () => {
    const page = form('2');
    for (const quantity of ['', '0', '-1', 'abc', 'Infinity']) {
        page.get('id_unit_price').value = '125';
        page.get('id_quantity').value = quantity;
        page.get('id_quantity').emit('input');
        assert.equal(page.get('id_unit_price').value, '');
    }
    page.get('id_quantity').value = '2';
    for (const amount of ['', '0', '-10', 'abc']) {
        page.get('id_unit_price').value = '125';
        page.get('id_amount').value = amount;
        page.get('id_amount').emit('input');
        assert.equal(page.get('id_unit_price').value, '');
    }
    page.type('fixed_income'); page.select('1');
    page.get('id_amount').value = '1000'; page.get('id_quantity').value = '10';
    page.get('id_amount').emit('input');
    assert.equal(page.get('id_unit_price').value, '');
    assert.equal(page.get('id_unit_price').disabled, true);
});
