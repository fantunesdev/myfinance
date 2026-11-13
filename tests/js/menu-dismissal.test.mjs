import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import { runInNewContext } from 'node:vm';

const source = await readFile(new URL('../../statement/static/js/scripts.js', import.meta.url), 'utf8');

function element(id = '', classes = []) {
    const names = new Set(classes);
    return {
        id, children: [], dataset: {}, attributes: {}, listeners: {},
        classList: {
            contains: name => names.has(name),
            add: name => names.add(name),
            remove: name => names.delete(name),
            toggle(name, open) {
                if (open) names.add(name);
                else names.delete(name);
            },
        },
        contains(target) { return this === target || this.children.some(child => child.contains(target)); },
        setAttribute(name, value) { this.attributes[name] = value; },
        addEventListener(name, handler) { this.listeners[name] = handler; },
        querySelector() { return this.arrow ?? null; },
        focus() { this.focused = true; },
    };
}

function page() {
    const ids = new Map();
    const buttons = [];
    for (const id of ['search', 'profile', 'conta-submenu', 'fatura-submenu']) {
        const menu = element(id, ['toggled']);
        menu.children.push(element());
        ids.set(id, menu);
        const button = element(`${id}-button`);
        button.dataset.menuTarget = id;
        button.children.push(element());
        if (id.endsWith('submenu')) button.arrow = element('', ['fa-angle-down', 'inverse-toggle']);
        buttons.push(button);
    }
    for (const id of ['id_search_description', 'sidebar-button', 'search-button']) ids.set(id, element(id));
    const body = element();
    body.children = [element(), element()];
    body.children[1].children = [element()];
    body.children[1].children[0].children = [element(), element()];
    const aside = element();
    const listeners = [];
    const document = {
        getElementById: id => ids.get(id) ?? null,
        getElementsByTagName: tag => [tag === 'body' ? body : aside],
        getElementsByClassName: () => [],
        querySelector(selector) {
            if (selector.startsWith('#')) return ids.get(selector.slice(1));
            return buttons.find(button => selector.includes(`"${button.dataset.menuTarget}"`));
        },
        querySelectorAll: () => buttons,
        addEventListener(type, handler, capture) { listeners.push({ type, handler, capture }); },
    };
    const context = { document, window: { location: { pathname: '/' }, innerWidth: 1200 } };
    runInNewContext(source, context);
    return {
        ...context, ids, buttons, body, aside,
        click(target, action = () => {}) {
            const clicks = listeners.filter(listener => listener.type === 'click');
            clicks.filter(listener => listener.capture).forEach(listener => listener.handler({ target }));
            action();
            clicks.filter(listener => !listener.capture).forEach(listener => listener.handler({ target }));
        },
        open(id) { return ids.get(id).classList.contains('active'); },
    };
}

for (const id of ['search', 'profile', 'conta-submenu', 'fatura-submenu']) {
    test(`${id}: opening click, internal click, outside click and reopening`, () => {
        const p = page();
        const button = p.buttons.find(button => button.dataset.menuTarget === id);
        const toggle = () => id.endsWith('submenu') ? p.toggleSubMenu(id) : p.toggleBox(id);
        p.click(button.children[0], toggle);
        assert.equal(p.open(id), true);
        assert.equal(button.attributes['aria-expanded'], 'true');
        p.click(p.ids.get(id).children[0]);
        assert.equal(p.open(id), true);
        p.click(element());
        assert.equal(p.open(id), false);
        assert.equal(button.attributes['aria-expanded'], 'false');
        if (button.arrow) {
            assert.equal(button.arrow.classList.contains('fa-angle-down'), true);
            assert.equal(button.arrow.classList.contains('fa-angle-up'), false);
            assert.equal(button.arrow.classList.contains('inverse-toggle'), true);
        }
        p.click(button, toggle);
        assert.equal(p.open(id), true);
        p.click(button, toggle);
        assert.equal(p.open(id), false);
    });
}

test('opening another menu closes the previous one', () => {
    const p = page();
    p.click(p.buttons[0], () => p.toggleBox('search'));
    assert.equal(p.ids.get('id_search_description').focused, true);
    p.click(p.buttons[1].children[0], () => p.toggleBox('profile'));
    assert.equal(p.open('search'), false);
    assert.equal(p.open('profile'), true);
});

test('mobile sidebar retains its outside click behavior', () => {
    const p = page();
    p.window.innerWidth = 600;
    const button = p.ids.get('sidebar-button');
    p.click(button, button.listeners.click);
    assert.equal(p.body.classList.contains('mobile-sidebar-open'), true);
    p.click(p.aside);
    assert.equal(p.body.classList.contains('mobile-sidebar-open'), true);
    p.click(element());
    assert.equal(p.body.classList.contains('mobile-sidebar-open'), false);
});
