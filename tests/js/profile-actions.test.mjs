import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import vm from 'node:vm';

const source = await readFile(new URL('../../statement/static/js/pages/user/get-profile.js', import.meta.url), 'utf8');
function setup(id, result) {
    const listeners = {}, modals = [], starts = [], sent = [];
    const button = { innerHTML: '', addEventListener: (name, fn) => { listeners[name] = fn; } };
    vm.runInNewContext(source.replace(/^import .*;\n/gm, ''), {
        Error, console: { error() {} },
        document: { getElementById: name => name === id ? button : null },
        window: { showModal: (title, message, confirm) => modals.push({ title, message, confirm }), hideModal() {} },
        services: { sendRequisition: async route => { sent.push(route); return result; } },
        startClassifierJob: async route => starts.push(route),
    });
    return { modals, starts, sent, async click() { listeners.click(); await modals[0].confirm(); } };
}

test('training buttons start asynchronous tracking without the legacy success modal', async () => {
    for (const id of ['subcategory-train-btn', 'description-train-btn', 'subcategory-feedback-btn', 'description-feedback-btn']) {
        const page = setup(id);
        await page.click();
        assert.equal(page.starts.length, 1);
        assert.equal(page.sent.length, 0);
        assert.equal(page.modals.length, 1);
    }
});

test('Error instances, explicit errors and failed business results cannot open the success modal', async () => {
    for (const result of [new SyntaxError('Unexpected token <'), { error: 'Erro real', message: 'Texto adicional' }, { success: false, message: 'Recusado' }]) {
        const page = setup('delete-feedbacks-btn', result);
        await page.click();
        assert.match(page.modals.at(-1).title, /Erro/);
        assert.equal(page.modals.some(modal => modal.title === 'Sucesso!'), false);
    }
});
