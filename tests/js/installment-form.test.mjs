import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import vm from 'node:vm';

const source = await readFile(new URL('../../statement/static/js/pages/transaction-form.js', import.meta.url), 'utf8');

test('formulário de parcelamento permite trocar cartão sem campos de combustível ou data de pagamento', async () => {
    function element(value = '') {
        return {
            value,
            style: {},
            classList: { add() {}, remove() {} },
            listeners: {},
            attributes: {},
            options: [],
            addEventListener(name, handler) { this.listeners[name] = handler; },
            appendChild(option) { this.options.push(option); },
            getAttribute(name) { return this.attributes[name]; },
            setAttribute(name, value) { this.attributes[name] = value; },
        };
    }
    const cardNumber = element('11');
    const wrapper = element();
    const selects = {
        paymentMethod: element('1'), account: element(), card: element('1'),
        postedDate: element('2026-06-08'), paymentDate: null,
        category: element(), subcategory: element(), value: element('100'),
        liters: null, price: null, km: null,
    };
    const divs = { account: element(), card: element() };
    const context = {
        selects, divs,
        enhanceSearchableSelect() { return null; },
        buttons: { otherOptions: element() },
        document: {
            readyState: 'complete',
            querySelector() { return null; },
            createElement() { return element(); },
            getElementById(id) {
                return { id_card: selects.card, id_card_number: cardNumber, 'div-card-number': wrapper }[id] || null;
            },
        },
        window: { card_numbers_json: [
            { id: 11, number: '1111', card_id: 1 },
            { id: 22, number: '2222', card_id: 2 },
        ] },
    };
    vm.runInNewContext(source.replace(/^import .*;\n/gm, ''), context);
    assert.equal(cardNumber.value, '11');
    assert.equal(wrapper.style.display, 'block');
    assert.equal(typeof selects.card.listeners.change, 'function');

    selects.card.value = '2';
    selects.card.listeners.change({ target: selects.card });
    await Promise.resolve();
    assert.equal(selects.paymentMethod.value, 1);
    assert.equal(cardNumber.options.at(-1).value, 22);
    selects.value.listeners.input();
});
