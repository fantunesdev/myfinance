import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import vm from 'node:vm';

const source = await readFile(new URL('../../statement/static/js/inactivity-logout.js', import.meta.url), 'utf8');
const settle = () => new Promise(resolve => setImmediate(resolve));

function browser() {
    const storage = new Map(), tabs = [];
    let now = 100000;
    function tab(overrides = {}) {
        const config = { session: 'browser-A', enabled: true, minutes: 1, revision: '',
            logoutUrl: '/logout-idle/', loginUrl: '/login/?inactive=1', ...overrides };
        const listeners = {}, elements = {}, classes = new Set(), requests = [], redirects = [], intervals = [];
        const emit = (type, data = {}) => {
            const event = { type, isTrusted: true, preventDefault() { this.prevented = true; }, stopImmediatePropagation() {}, ...data };
            for (const fn of listeners[type] || []) fn(event);
            return event;
        };
        const add = (type, fn) => { (listeners[type] ??= []).push(fn); };
        const document = {
            visibilityState: 'visible',
            documentElement: { classList: { add: key => classes.add(key), remove: key => classes.delete(key) } },
            body: { appendChild: element => { elements[element.id] = element; } },
            createElement: () => ({ setAttribute() {} }),
            getElementById: key => key === 'inactivity-logout-config' ? { textContent: JSON.stringify(config) } : elements[key],
            querySelector: () => ({ content: 'csrf-token' }), addEventListener: add,
        };
        const page = { emit, document, requests, redirects, config, classes, offline: false,
            tick: () => intervals.forEach(fn => fn()) };
        tabs.push(page);
        vm.runInNewContext(source, {
            document, Date: { now: () => now }, Map, JSON, Math, URLSearchParams,
            Event: class { constructor(type) { this.type = type; } },
            window: { addEventListener: add, dispatchEvent: event => emit(event.type, event) },
            localStorage: {
                getItem: key => storage.get(key) ?? null,
                setItem(key, value) {
                    if (storage.get(key) === value) return;
                    storage.set(key, value);
                    for (const other of tabs) if (other !== page) other.emit('storage', { key, newValue: value });
                },
            },
            sessionStorage: {},
            location: { replace: url => redirects.push(url) },
            fetch: async (url, options) => {
                requests.push({ url, options });
                if (page.offline) throw new Error('offline');
                return { ok: true, status: 200 };
            },
            setInterval: fn => intervals.push(fn),
        });
        return page;
    }
    return { tab, storage, advance: ms => { now += ms; } };
}

test('expiry hides data immediately and logs out with POST and CSRF', async () => {
    const b = browser(), page = b.tab();
    b.advance(60000); page.tick();
    assert.ok(page.classes.has('myfinance-privacy-hidden'));
    assert.equal(page.requests.length, 1);
    assert.equal(page.requests[0].options.method, 'POST');
    assert.equal(page.requests[0].options.headers['X-CSRFToken'], 'csrf-token');
    assert.equal(page.requests[0].options.body.get('session'), 'browser-A');
    await settle();
    assert.deepEqual(page.redirects, ['/login/?inactive=1']);
});

test('activity in either tab extends both deadlines; expiry reaches all tabs', () => {
    const b = browser(), a = b.tab(), other = b.tab();
    b.advance(50000); other.emit('keydown');
    b.advance(10000); a.tick(); other.tick();
    assert.equal(a.requests.length + other.requests.length, 0);
    b.advance(50000); a.tick();
    assert.equal(a.requests.length, 1);
    assert.equal(other.requests.length, 1);
    assert.ok(other.classes.has('myfinance-privacy-hidden'));
});

test('a late interaction is intercepted and cannot renew access', () => {
    const b = browser(), page = b.tab();
    b.advance(60001);
    assert.equal(page.emit('pointerdown').prevented, true);
    assert.equal(page.requests.length, 1);
});

test('focus, restoring a page and background updates do not reset the clock', () => {
    for (const event of ['focus', 'pageshow', 'visibilitychange', 'investments:changed']) {
        const b = browser(), page = b.tab();
        b.advance(50000); page.emit(event);
        b.advance(10000); page.tick();
        assert.equal(page.requests.length, 1, event);
    }
});

test('background tabs conceal data and check expiry on wake without a timer', () => {
    const b = browser(), page = b.tab();
    page.document.visibilityState = 'hidden'; page.emit('visibilitychange');
    assert.ok(page.classes.has('myfinance-privacy-hidden'));
    b.advance(61000);
    page.document.visibilityState = 'visible'; page.emit('visibilitychange');
    assert.equal(page.requests.length, 1);
    assert.ok(page.classes.has('myfinance-privacy-hidden'));
});

test('switching back before expiry reveals the content', () => {
    const b = browser(), page = b.tab();
    page.document.visibilityState = 'hidden'; page.emit('visibilitychange');
    b.advance(30000);
    page.document.visibilityState = 'visible'; page.emit('visibilitychange');
    assert.equal(page.classes.size, 0);
});

test('disabled setting never expires and a new setting propagates to existing tabs', () => {
    const b = browser(), page = b.tab({ enabled: false });
    b.advance(900000); page.tick();
    assert.equal(page.requests.length, 0);
    b.tab({ enabled: true, revision: '100' });
    b.advance(60000); page.tick();
    assert.equal(page.requests.length, 1);
});

test('disabling propagates, and an old page cannot override newer preferences', () => {
    const b = browser(), page = b.tab();
    b.tab({ enabled: false, revision: '100' });
    b.tab();
    b.advance(120000); page.tick();
    assert.equal(page.requests.length, 0);
});

test('reload and opening another tab cannot reset an expired deadline', () => {
    const b = browser(); b.tab(); b.advance(61000);
    const page = b.tab({ revision: '200' });
    assert.equal(page.requests.length, 1);
});

test('offline expiry remains concealed and retries on reconnection', async () => {
    const b = browser(), page = b.tab(); page.offline = true;
    b.advance(60000); page.tick();
    await settle();
    assert.ok(page.classes.has('myfinance-privacy-hidden'));
    assert.equal(page.redirects.length, 0);
    page.offline = false; page.emit('online');
    await settle();
    assert.equal(page.requests.length, 2);
    assert.equal(page.redirects.length, 1);
});

test('a new login uses a separate deadline from expired old pages', () => {
    const b = browser(), old = b.tab();
    b.advance(60000); old.tick();
    const fresh = b.tab({ session: 'browser-B' });
    assert.equal(fresh.requests.length, 0);
    assert.equal(fresh.classes.size, 0);
});
