export const DEFAULT_STATE = Object.freeze({ assetType: '', chartMode: 'progression', showAllPositions: false, showAllBrokers: false });
const TYPES = ['fixed_income', 'variable_income', 'crypto'];
export const MAX_AGE = 5 * 60 * 1000;

export function normalizeState(state = {}) {
    return {
        assetType: TYPES.includes(state.assetType) ? state.assetType : '',
        chartMode: state.chartMode === 'interest' ? 'interest' : 'progression',
        showAllPositions: state.showAllPositions === true,
        showAllBrokers: state.showAllBrokers === true,
    };
}

export function stateFromUrl(url, saved = DEFAULT_STATE) {
    const params = new URL(url).searchParams;
    if (!['asset_type', 'positions', 'brokers', 'chart'].some(key => params.has(key))) return normalizeState(saved);
    return normalizeState({
        assetType: params.get('asset_type'), chartMode: params.get('chart'),
        showAllPositions: params.get('positions') === 'all', showAllBrokers: params.get('brokers') === 'all',
    });
}

export function stateUrl(url, state) {
    const next = new URL(url);
    for (const [key, value] of Object.entries({
        asset_type: state.assetType, positions: state.showAllPositions ? 'all' : '',
        brokers: state.showAllBrokers ? 'all' : '', chart: state.chartMode === 'interest' ? 'interest' : '',
    })) {
        if (value) next.searchParams.set(key, value);
        else next.searchParams.delete(key);
    }
    return next;
}

export function validPayload(data, userId) {
    const numeric = value => ['string', 'number'].includes(typeof value)
        && String(value).trim() !== '' && Number.isFinite(Number(value));
    const series = value => Array.isArray(value) && value.every(item => item && typeof item.label === 'string'
        && typeof item.color === 'string' && Array.isArray(item.names) && Array.isArray(item.values)
        && item.names.length === item.values.length && item.values.every(numeric));
    return data?.schema_version === 1 && String(data.user_id) === String(userId)
        && ['total', 'net_income', 'available_to_invest'].every(key => numeric(data.totals?.[key]))
        && Array.isArray(data.positions) && data.positions.every(item => item && Number.isInteger(item.id)
            && typeof item.label === 'string' && typeof item.asset_type === 'string'
            && typeof item.asset_type_label === 'string' && typeof item.broker === 'string'
            && typeof item.url === 'string' && item.url.startsWith('/') && !item.url.startsWith('//')
            && numeric(item.value) && numeric(item.quantity))
        && Array.isArray(data.brokers) && data.brokers.every(item => item && typeof item.label === 'string' && numeric(item.value))
        && series(data.progression_datasets) && series(data.interest_datasets);
}

export function createInvestmentStore({ userId, apiUrl, storage, fetcher = (...args) => fetch(...args), now = Date.now }) {
    const prefix = `myfinance:investments:v1:${userId}:`;
    const read = key => { try { return JSON.parse(storage?.getItem(prefix + key) || 'null'); } catch { return null; } };
    const write = (key, value) => { try { storage?.setItem(prefix + key, JSON.stringify(value)); } catch { /* Memory cache remains usable. */ } };
    let cached = read('data');
    if (!validPayload(cached?.data, userId)) cached = null;
    let state = normalizeState(read('state') || DEFAULT_STATE);
    let generation = 0;
    let inFlight = null;
    let invalidatedRevision;

    function clear() {
        cached = null;
        generation++;
        for (const key of ['data', 'state', 'changed']) {
            try { storage?.removeItem(prefix + key); } catch { /* Storage unavailable. */ }
        }
    }
    function isFresh() {
        const changed = read('changed');
        return !!cached && cached.expiresAt > now()
            && !(changed && changed.at >= cached.fetchedAt && (!changed.revision || changed.revision !== cached.data.revision));
    }
    function invalidate(revision) {
        if (revision && (revision === cached?.data.revision || revision === invalidatedRevision)) return false;
        invalidatedRevision = revision;
        generation++;
        if (cached) { cached.expiresAt = 0; write('data', cached); }
        return true;
    }
    async function request() {
        for (let attempt = 0; attempt < 2; attempt++) {
            const start = generation;
            const headers = { Accept: 'application/json' };
            if (cached?.etag) headers['If-None-Match'] = cached.etag;
            const response = await fetcher(apiUrl, { headers, credentials: 'same-origin', cache: 'no-cache' });
            if (response.status === 401 || response.status === 403) {
                clear();
                const error = new Error('Sua sessão expirou. Entre novamente para consultar os investimentos.');
                error.auth = true;
                throw error;
            }
            let data, etag;
            if (response.status === 304 && cached) {
                data = cached.data;
                etag = cached.etag;
            } else {
                if (!response.ok || !(response.headers.get('content-type') || '').includes('application/json')) {
                    throw new Error('Não foi possível atualizar os investimentos. Tente novamente.');
                }
                data = await response.json();
                if (!validPayload(data, userId)) throw new Error('A resposta dos investimentos é inválida. Tente novamente.');
                etag = response.headers.get('etag');
            }
            if (generation !== start && (!invalidatedRevision || data.revision !== invalidatedRevision)) continue;
            cached = { data, etag, fetchedAt: now(), expiresAt: now() + MAX_AGE };
            invalidatedRevision = undefined;
            write('data', cached);
            try { storage?.removeItem(prefix + 'changed'); } catch { /* Storage unavailable. */ }
            return data;
        }
        throw new Error('Os investimentos foram alterados durante a consulta. Tente novamente.');
    }
    function load({ force = false } = {}) {
        if (inFlight) return inFlight;
        if (!force && isFresh()) return Promise.resolve(cached.data);
        inFlight = request().finally(() => { inFlight = null; });
        return inFlight;
    }
    return {
        load, clear, invalidate, isFresh,
        peek: () => cached?.data || null,
        getState: () => ({ ...state }),
        setState: next => { state = normalizeState(next); write('state', state); return { ...state }; },
    };
}
