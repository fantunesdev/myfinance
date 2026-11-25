import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import vm from 'node:vm';

const source = await readFile(new URL('../../statement/static/js/toasts.js', import.meta.url), 'utf8');
function setup() {
    let now = 0, serial = 0;
    const timers = new Map();
    class Element {
        constructor() { this.children = []; this.dataset = {}; this.events = {}; this.attributes = {}; }
        append(...children) { children.forEach(child => { child.parent = this; this.children.push(child); }); }
        setAttribute(key, value) { this.attributes[key] = value; }
        addEventListener(key, fn) { (this.events[key] ??= []).push(fn); }
        emit(key, event = {}) { (this.events[key] || []).forEach(fn => fn(event)); }
        querySelectorAll(selector) { return this.children.flatMap(child => [...(child.className === selector.slice(1) ? [child] : []), ...child.querySelectorAll(selector)]); }
        querySelector(selector) { return this.querySelectorAll(selector)[0]; }
        contains(element) { return this === element || this.children.some(child => child.contains(element)); }
        remove() { this.parent.children = this.parent.children.filter(child => child !== this); }
    }
    const stack = new Element();
    const document = new Element();
    document.hidden = false;
    document.getElementById = () => stack;
    document.createElement = () => new Element();
    const window = {};
    vm.runInNewContext(source, {
        document, window, Date: { now: () => now },
        setTimeout(fn, delay) { const id = ++serial; timers.set(id, { fn, end: now + delay }); return id; },
        clearTimeout(id) { timers.delete(id); },
    });
    return { stack, document, show: window.myFinanceToast, tick(ms) {
        now += ms;
        for (const [id, timer] of [...timers]) if (timer.end <= now) { timers.delete(id); timer.fn(); }
    } };
}

test('each toast closes after 20 seconds or immediately using its close button', () => {
    const page = setup();
    page.show('Salvo', 'success');
    page.tick(19000);
    page.show('Erro', 'error');
    page.tick(1000);
    assert.equal(page.stack.children.length, 1);
    assert.equal(page.stack.children[0].dataset.toastLevel, 'error');
    page.stack.children[0].querySelector('.toast-close').emit('click');
    assert.equal(page.stack.children.length, 0);
    page.tick(30000);
    assert.equal(page.stack.children.length, 0);
});

test('hover, keyboard focus and a hidden tab pause expiration without resetting elapsed time', () => {
    for (const mode of ['pointer', 'focus', 'visibility']) {
        const page = setup();
        page.show('Leia esta mensagem', 'warning');
        const toast = page.stack.children[0];
        page.tick(5000);
        if (mode === 'pointer') toast.emit('pointerenter');
        if (mode === 'focus') toast.emit('focusin');
        if (mode === 'visibility') { page.document.hidden = true; page.document.emit('visibilitychange'); }
        page.tick(30000);
        assert.equal(page.stack.children.length, 1);
        if (mode === 'pointer') toast.emit('pointerleave');
        if (mode === 'focus') toast.emit('focusout', { relatedTarget: null });
        if (mode === 'visibility') { page.document.hidden = false; page.document.emit('visibilitychange'); }
        page.tick(14999);
        assert.equal(page.stack.children.length, 1);
        page.tick(1);
        assert.equal(page.stack.children.length, 0);
    }
});

test('untrusted text remains text and unknown levels fall back to information', () => {
    const page = setup();
    const message = '<img src=x onerror=alert(1)>';
    page.show(message, '__proto__');
    const toast = page.stack.children[0];
    assert.equal(toast.dataset.toastLevel, 'info');
    assert.equal(toast.attributes.role, 'status');
    assert.equal(toast.querySelector('.toast-content').children[1].textContent, message);
    assert.equal(toast.querySelector('.toast-close').attributes['aria-label'], 'Fechar notificação');
});

test('rapid actions keep only the three latest messages instead of covering the screen', () => {
    const page = setup();
    for (let i = 0; i < 5; i++) page.show(`Mensagem ${i}`, 'success');
    assert.equal(page.stack.children.length, 3);
    assert.equal(page.stack.children[0].querySelector('.toast-content').children[1].textContent, 'Mensagem 2');
    page.tick(20000);
    assert.equal(page.stack.children.length, 0);
});
