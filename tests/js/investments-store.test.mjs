import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const source = await readFile(new URL('../../statement/static/js/data/investments-store.js', import.meta.url), 'utf8');
const { createInvestmentStore, stateFromUrl, stateUrl, MAX_AGE } = await import(`data:text/javascript,${encodeURIComponent(source)}`);
function storage() {
    const values = new Map();
    return { values, getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key) };
}
const payload = (revision = 'a', user_id = 1) => ({ schema_version: 1, user_id, revision,
    totals: { total: '100', net_income: '10', available_to_invest: '0' },
    positions: [], brokers: [], progression_datasets: [], interest_datasets: [], has_default_wallet: true });
function response(data, status = 200, etag = '"a"') {
    return { status, ok: status === 200, headers: { get: key => key === 'content-type' ? 'application/json' : etag }, json: async () => data };
}

test('shares one request and reuses session cache after page navigation', async () => {
    const disk = storage(); let calls = 0;
    const options = { userId: 1, apiUrl: '/api/dashboard/', storage: disk, fetcher: async () => { calls++; return response(payload()); } };
    const store = createInvestmentStore(options);
    await Promise.all([store.load(), store.load(), store.load()]);
    assert.equal(calls, 1);
    store.setState({ assetType: 'fixed_income', showAllPositions: true });
    await store.load();
    const nextPage = createInvestmentStore(options);
    await nextPage.load();
    assert.equal(calls, 1);
    assert.equal(nextPage.getState().assetType, 'fixed_income');
    assert.equal(nextPage.getState().showAllPositions, true);
});

test('expiration uses conditional GET; 304 retains snapshot', async () => {
    let time = 100, calls = 0;
    const store = createInvestmentStore({ userId: 1, storage: storage(), now: () => time,
        fetcher: async (url, options) => {
            calls++;
            if (calls === 1) return response(payload());
            assert.equal(options.headers['If-None-Match'], '"a"');
            return response(null, 304);
        } });
    await store.load();
    time += MAX_AGE + 1;
    assert.equal(store.isFresh(), false);
    assert.equal((await store.load()).revision, 'a');
    assert.equal(store.isFresh(), true);
    assert.equal(calls, 2);
});

test('known notifications are deduplicated; newer revision refreshes once', async () => {
    let calls = 0;
    const store = createInvestmentStore({ userId: 1, storage: storage(), fetcher: async () => response(payload(++calls === 1 ? 'a' : 'b')) });
    await store.load();
    assert.equal(store.invalidate('a'), false);
    assert.equal(store.invalidate('b'), true);
    assert.equal(store.invalidate('b'), false);
    await Promise.all([store.load(), store.load()]);
    assert.equal(calls, 2);
    assert.equal(store.peek().revision, 'b');
});

test('invalidation during a request cannot overwrite a newer revision with stale response', async () => {
    let release, calls = 0;
    const store = createInvestmentStore({ userId: 1, storage: storage(), fetcher: async () => {
        calls++;
        if (calls === 1) await new Promise(resolve => { release = resolve; });
        return response(payload(calls === 1 ? 'a' : 'b'));
    } });
    const loading = store.load();
    store.invalidate('b'); release();
    assert.equal((await loading).revision, 'b');
    assert.equal(calls, 2);
});

test('initial ready event matching incoming response does not cause a second request', async () => {
    let release, calls = 0;
    const store = createInvestmentStore({ userId: 1, storage: storage(), fetcher: async () => {
        calls++; await new Promise(resolve => { release = resolve; }); return response(payload('b'));
    } });
    const loading = store.load(); store.invalidate('b'); release();
    await loading; assert.equal(calls, 1);
});

test('failed update preserves last good data; unauthorized response clears user cache', async () => {
    let status = 200;
    const disk = storage();
    const store = createInvestmentStore({ userId: 1, storage: disk, fetcher: async () => response(payload(), status) });
    await store.load();
    status = 500;
    await assert.rejects(store.load({ force: true }));
    assert.equal(store.peek().revision, 'a');
    status = 403;
    await assert.rejects(store.load({ force: true }), error => error.auth === true);
    assert.equal(store.peek(), null);
    assert.equal(disk.getItem('myfinance:investments:v1:1:data'), null);
});

test('corrupt, foreign-user and unavailable storage all recover via API', async () => {
    for (const invalid of ['{bad', JSON.stringify({ data: payload('a', 2), expiresAt: Infinity }), JSON.stringify({ data: { ...payload(), positions: [null] } })]) {
        const disk = storage(); disk.setItem('myfinance:investments:v1:1:data', invalid);
        let calls = 0;
        const store = createInvestmentStore({ userId: 1, storage: disk, fetcher: async () => { calls++; return response(payload()); } });
        await store.load(); assert.equal(calls, 1);
    }
    const unavailable = { getItem() { throw Error(); }, setItem() { throw Error(); }, removeItem() { throw Error(); } };
    const store = createInvestmentStore({ userId: 1, storage: unavailable, fetcher: async () => response(payload()) });
    await store.load(); assert.equal(store.isFresh(), true);
});

test('mutation marker received on another page invalidates only old snapshot', async () => {
    const disk = storage(); let time = 100;
    const store = createInvestmentStore({ userId: 1, storage: disk, now: () => time, fetcher: async () => response(payload()) });
    await store.load();
    disk.setItem('myfinance:investments:v1:1:changed', JSON.stringify({ at: ++time, revision: null }));
    assert.equal(store.isFresh(), false);
    await store.load(); assert.equal(store.isFresh(), true);
});

test('URL explicitly selects state; clearing category preserves other selections', () => {
    const state = stateFromUrl('https://test/investimentos/?asset_type=fixed_income&positions=all&brokers=all');
    const url = stateUrl('https://test/investimentos/?asset_type=fixed_income', { ...state, assetType: '' });
    assert.equal(url.searchParams.has('asset_type'), false);
    assert.equal(url.searchParams.get('positions'), 'all');
    assert.equal(url.searchParams.get('brokers'), 'all');
    assert.equal(stateFromUrl('https://test/investimentos/', state).assetType, 'fixed_income');
});
