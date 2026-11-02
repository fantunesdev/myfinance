import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import vm from 'node:vm';

const notificationSource = await readFile(new URL('../../statement/static/js/pages/import-notifications.js', import.meta.url), 'utf8');
const csvSource = await readFile(new URL('../../statement/static/js/pages/import-transactions.js', import.meta.url), 'utf8');
const eventSource = await readFile(new URL('../../statement/static/js/pages/import-event.js', import.meta.url), 'utf8');

function setup(source = notificationSource) {
    const elements = new Map();
    class Element {
        constructor() { this.children = []; this.listeners = {}; this.classList = { add() {}, toggle() {} }; this.value = ''; }
        appendChild(child) { this.children.push(child); if (child.id) elements.set(String(child.id), child); }
        setAttribute() {}
        addEventListener(name, callback) { this.listeners[name] = callback; }
        dispatchEvent(event) { this.listeners[event.type]?.(); }
    }
    const document = { createElement: () => new Element(), getElementById: id => elements.get(String(id)) || null };
    const context = vm.createContext({ document, Event: class { constructor(type) { this.type = type; } } });
    vm.runInContext(eventSource.replace(/^export /gm, ''), context);
    const functions = source.slice(source.indexOf('function getFormData('), source.indexOf('/**\n * Método acessório de import' + (source === notificationSource ? 'Notifications' : 'Transactions') + ' que cria um novo recurso'));
    vm.runInContext(functions, context);
    return { context, document, elements, Element };
}

test('notification feedback retains actual prediction input and full original message', () => {
    const { context } = setup();
    const original = { id: 1, notification_id: 9, source_type: 'notification', source_app: 'bank', original_description: 'Compra R$ 10 em RAIA3419', merchant_description: 'RAIA3419', description: 'Farmácia', category: 1, subcategory: 10, event_type: 'purchase' };
    const feedback = context.buildFeedback(original, { description: 'Saúde', category: '1', subcategory: '11' });
    assert.equal(feedback.description, 'RAIA3419');
    assert.equal(feedback.merchant_description, 'RAIA3419');
    assert.equal(feedback.original_description, original.original_description);
    assert.equal(feedback.source_notification, 9);
});

test('unchanged notification IDs submitted as strings do not create feedback', () => {
    const { context } = setup();
    assert.equal(context.buildFeedback({ description: 'Farmácia', category: 1, subcategory: 10 }, { description: 'Farmácia', category: '1', subcategory: '10' }), null);
});

test('card payment classification does not feed purchase predictors', () => {
    for (const source of [notificationSource, csvSource]) {
        const { context } = setup(source);
        assert.equal(context.buildFeedback({ description: 'Fatura', event_type: 'card_payment' }, { description: 'Pagamento', category: 1, subcategory: 10 }), null);
    }
});

test('a failed merchant extraction remains empty in metadata instead of learning the notification template', () => {
    const { context } = setup();
    const metadata = context.eventMetadata(1, { source_type: 'notification', original_description: 'Compra aprovada no cartão', merchant_description: '' });
    assert.equal(metadata.merchant_description, '');
    assert.equal(metadata.original_description, 'Compra aprovada no cartão');
});

test('special events require review and ignoring only changes the explicit user selection', () => {
    const { context, elements, Element } = setup();
    const checkbox = new Element(); checkbox.checked = false; elements.set('1', checkbox);
    const cell = new Element();
    context.renderEventReview(cell, { id: 1, event_type: 'card_payment', needs_review: true, review_reason: 'Pagamento da fatura' });
    const action = elements.get('id_event_action_1');
    assert.equal(action.value, 'review');
    assert.equal(checkbox.checked, false);
    action.value = 'import'; action.dispatchEvent({ type: 'change' });
    assert.equal(checkbox.checked, true);
    action.value = 'ignore'; action.dispatchEvent({ type: 'change' });
    assert.equal(checkbox.checked, false);
    assert.equal(context.importAction(1), 'ignore');
    const metadata = context.eventMetadata(1, {});
    assert.equal(metadata.event_type, 'card_payment');
});

test('abstentions keep a blank selection and string IDs still select the actual prediction', () => {
    for (const source of [notificationSource, csvSource]) {
        const { context } = setup(source);
        const start = source.indexOf('function createSelect(');
        const end = source.indexOf('function updateSelectOptions(', start);
        vm.runInContext(source.slice(start, end), context);
        const empty = context.createSelect({ options: [{ id: 1, description: 'Alimentação' }] });
        assert.equal(empty.children[0].value, '');
        assert.notEqual(empty.children[1].selected, true);
        const predicted = context.createSelect({ options: [{ id: 1, description: 'Alimentação' }], selected: '1' });
        assert.equal(predicted.children[1].selected, true);
    }
});
