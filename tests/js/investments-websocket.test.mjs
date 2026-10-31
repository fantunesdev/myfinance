import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import vm from 'node:vm';

const source = await readFile(new URL('../../statement/static/js/websocket.js', import.meta.url), 'utf8');
function setup(userId = '1') {
    const events = {}, documentEvents = {}, sockets = [], timers = [], storage = {};
    const sessionStorage = {
        getItem: key => storage[key] ?? null,
        setItem: (key, value) => { storage[key] = value; Object.defineProperty(sessionStorage, key, { enumerable: true, configurable: true }); },
        removeItem: key => { delete storage[key]; delete sessionStorage[key]; },
    };
    class WebSocket {
        static OPEN = 1; static CONNECTING = 0;
        constructor(url) { this.url = url; this.readyState = 0; sockets.push(this); }
        close(code = 1000) { this.readyState = 3; this.onclose?.({ code }); }
        message(data) { this.onmessage({ data: JSON.stringify(data) }); }
    }
    const received = [];
    const window = { addEventListener: (name, fn) => { events[name] = fn; }, dispatchEvent: event => received.push(event) };
    const document = { querySelector: () => userId ? { content: userId } : null, addEventListener: (name, fn) => { documentEvents[name] = fn; } };
    vm.runInNewContext(source, { document, window, sessionStorage, WebSocket, URL, Date, Math, console,
        location: { protocol: 'https:', host: 'test', href: 'https://test/investimentos/' },
        CustomEvent: class { constructor(type, options) { this.type = type; this.detail = options?.detail; } },
        setTimeout: (fn, delay) => { const timer = { fn, delay }; timers.push(timer); return timer; }, clearTimeout: timer => { if (timer) timer.cancelled = true; },
    });
    return { window, events, documentEvents, sockets, timers, received, storage, sessionStorage };
}

test('socket invalidates only changed revisions and retains existing shared messages', () => {
    const page = setup();
    const key = 'myfinance:investments:v1:1:';
    page.sessionStorage.setItem(key + 'data', JSON.stringify({ data: { revision: 'a' } }));
    const socket = page.sockets[0]; assert.equal(socket.url, 'wss://test/ws/');
    socket.message({ type: 'investments.ready', revision: 'a' }); assert.equal(page.received.length, 0);
    socket.message({ type: 'investments.changed', revision: 'b' });
    assert.equal(page.received.length, 1);
    assert.equal(JSON.parse(page.storage[key + 'changed']).revision, 'b');
    socket.message({ data: { categories: [{ id: 1 }] } });
    assert.deepEqual(JSON.parse(page.storage.categories), [{ id: 1 }]);
    page.events['investments:mutation']();
    assert.equal(page.received.length, 2);
    assert.equal(JSON.parse(page.storage[key + 'changed']).revision, null);
});

test('reconnects with backoff, avoids duplicate sockets and clears investment cache on logout', () => {
    const page = setup();
    page.events.pageshow(); assert.equal(page.sockets.length, 1);
    page.sockets[0].close(1006);
    assert.ok(page.timers[0].delay >= 1000 && page.timers[0].delay < 1200);
    page.timers[0].fn(); assert.equal(page.sockets.length, 2);
    page.sockets[1].close(1006);
    assert.ok(page.timers[1].delay >= 2000 && page.timers[1].delay < 2200);
    page.sessionStorage.setItem('myfinance:investments:v1:1:data', 'private');
    page.sessionStorage.setItem('categories', 'keep');
    page.documentEvents.click({ target: { closest: () => true } });
    assert.equal(page.storage['myfinance:investments:v1:1:data'], undefined);
    assert.equal(page.storage.categories, 'keep');
    assert.equal(page.timers[1].cancelled, true);
    page.timers[1].fn(); assert.equal(page.sockets.length, 2);
    assert.equal(setup('').sockets.length, 0);
});
