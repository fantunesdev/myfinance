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

test('event type stays editable without an action selector or changes to checkbox selection', () => {
    const { context, elements, Element } = setup();
    const checkbox = new Element(); checkbox.checked = false; elements.set('1', checkbox);
    const cell = new Element();
    context.renderEventType(cell, { id: 1, event_type: 'card_payment', needs_review: true, review_reason: 'Confira os dados.' });
    const event = elements.get('id_event_type_1');
    assert.equal(event.value, 'card_payment');
    assert.equal(elements.has('id_event_action_1'), false);
    assert.equal(cell.children[0].children.filter(child => child.id?.startsWith('id_event_')).length, 1);
    assert.equal(checkbox.checked, false);
    checkbox.checked = true;
    event.value = 'refund';
    event.dispatchEvent({ type: 'change' });
    assert.equal(checkbox.checked, true);
    assert.equal(context.eventMetadata(1, {}).event_type, 'refund');
});

test('CSV and notification previews place the event selector after value, outside description', () => {
    for (const source of [notificationSource, csvSource]) {
        const { context, Element, elements } = setup(source);
        context.selects = { card: { value: '' } };
        context.window = { myFinance: { hasCSVInstallments: false } };
        context.getCardNumbersByCard = () => [];
        vm.runInContext(source.slice(source.indexOf('function getTransactionFields('), source.indexOf('function renderFields(')), context);
        const fields = context.getTransactionFields({ id: 1, description: 'Compra', event_type: 'purchase' }, [], []);
        const valueIndex = fields.findIndex(field => field.id === 'id_value_1');
        assert.equal(fields[valueIndex + 1].id, 'id_event_type_1');
        const descriptionCell = new Element();
        fields.find(field => field.id === 'id_description_1').render(descriptionCell);
        assert.equal(descriptionCell.children.length, 1);
        assert.equal(elements.has('id_event_type_1'), false);
        const eventCell = new Element();
        fields[valueIndex + 1].render(eventCell);
        assert.equal(elements.get('id_event_type_1').value, 'purchase');
    }
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
