import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import vm from 'node:vm';

const source = (await readFile(new URL('../../statement/static/js/pages/import-tasker.js', import.meta.url), 'utf8'))
    .replace(/^import .*;$/gm, '');

function setup() {
    const elements = new Map();
    const timers = [];
    function element(selector) {
        if (!elements.has(selector)) {
            const classes = new Set();
            elements.set(selector, {
                checked: false, value: '', children: [], listeners: {},
                classList: {
                    add: value => classes.add(value), remove: value => classes.delete(value),
                    contains: value => classes.has(value),
                },
                addEventListener(name, callback) { this.listeners[name] = callback; },
            });
        }
        return elements.get(selector);
    }
    const context = vm.createContext({
        document: { querySelector: element, cookie: '' },
        setTimeout: fn => timers.push(fn),
        fetch: async () => ({ ok: true }),
    });
    vm.runInContext(source, context);
    return { context, element, timers };
}

test('Tasker initializes and switches between configurable CSV and JSON forms', () => {
    const { element } = setup();
    element('#file-type-configurable-csv').checked = true;
    element('#file-type-configurable-csv').listeners.change();
    assert.equal(element('#form-csv').classList.contains('toggled'), false);
    assert.equal(element('#form-tasker').classList.contains('toggled'), true);
    element('#file-type-configurable-csv').checked = false;
    element('#file-type-tasker').checked = true;
    element('#file-type-tasker').listeners.change();
    assert.equal(element('#form-csv').classList.contains('toggled'), true);
    assert.equal(element('#form-tasker').classList.contains('toggled'), false);
    assert.equal(typeof element('#import-tasker-btn').listeners.click, 'function');
});

test('saving Tasker notifications resets the file and selects configurable CSV', async () => {
    const { context, element, timers } = setup();
    element('#file-type-tasker').checked = true;
    element('#id_file_tasker').value = 'notifications.json';
    await context.saveNotifications([{ app: 'bank', title: 'Compra', message: 'R$ 10', date: '2026-11-02' }]);
    assert.equal(timers.length, 1);
    timers[0]();
    assert.equal(element('#file-type-configurable-csv').checked, true);
    assert.equal(element('#file-type-tasker').checked, false);
    assert.equal(element('#id_file_tasker').value, '');
    assert.equal(element('#form-tasker').classList.contains('toggled'), true);
});
