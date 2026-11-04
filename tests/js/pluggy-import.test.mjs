import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import vm from 'node:vm';

const source = await readFile(new URL('../../bank_sync/static/bank_sync/import.js', import.meta.url), 'utf8');
const flush = () => new Promise(resolve => setImmediate(resolve));

class Element {
    constructor(tag = 'div') {
        this.tag = tag;
        this.children = [];
        this.style = {};
        this.value = '';
        this.listeners = {};
        this.dataset = {};
        this.classList = { add() {}, toggle() {}, remove() {} };
    }
    append(child) { this.children.push(child); }
    replaceChildren() { this.children = []; }
    setAttribute(key, value) { this[key] = value; }
    addEventListener(name, callback) { this.listeners[name] = callback; }
    querySelector() { return { value: 'csrf-test' }; }
    all() { return [this, ...this.children.flatMap(c => c.all())]; }
}
function setup(row = null, active = true) {
    const elements = new Map();
    const get = id => {
        if (!elements.has(id)) elements.set(id, new Element());
        return elements.get(id);
    };
    get('pluggy-import').dataset.stateUrl = '/relatorio_financeiro/importar/pluggy/state/';
    get('pluggy-state').value = 'new';
    get('import-type-pluggy').checked = active;
    const calls = [];
    const payload = {
        configured: true, accounts: [], connections: [], rows: row ? [row] : [],
        count: row ? 1 : 0, page: 1, pages: 1,
        cards: [], card_numbers: [], categories: [], subcategories: [], bills: [], selected_bill: 'all',
    };
    const context = vm.createContext({ URLSearchParams, window: { location: { search: '' } },
        document: { getElementById: get, createElement: tag => new Element(tag) },
        fetch: async (url, options) => {
            calls.push({ url, options });
            return { ok: true, headers: { get: () => 'application/json' },
                json: async () => url.includes('prepare/') ? payload : {} };
        },
    });
    vm.runInContext(source, context);
    return { get, calls, context };
}
function row(extra = {}) {
    return { id: 1, revision: 2, state: 'new', due_date: '2026-11-10', event: 'purchase',
        card_number: {id:1, name:'Test card'},
        facts: { description: '<img src=x onerror=alert(1)>', date: '2026-10-20', amount: '10.00', currency: 'BRL',
            payment_type: 'INSTALLMENT', number: 2, total: 3, status: 'POSTED', last_four: '1234' },
        ...extra };
}

test('source text is rendered as text; initial load never confirms transactions', async () => {
    const page = setup(row());
    await flush();
    assert.equal(page.calls.length, 1);
    assert.ok(page.calls[0].url.endsWith('prepare/'));
    assert.ok(page.calls.every(call => !call.url.endsWith('review/')));
    const description = page.get('pluggy-rows').all().find(n => n.title?.startsWith('Original:'));
    assert.ok(description.title.includes('<img src=x onerror=alert(1)>'));
    assert.ok(page.get('pluggy-rows').all().every(n => n.tag !== 'small'));
    assert.ok(page.get('pluggy-rows').all().every(n => n.innerHTML === undefined));
});

test('create uses dedicated review endpoint, explicit projection flag, revision and CSRF', async () => {
    const page = setup(row());
    await flush();
    const controls = page.get('pluggy-rows').all();
    const checkbox = controls.find(n => n.type === 'checkbox' && controls.some(label =>
        label.textContent?.includes('Projetar parcelas') && label.children.includes(n)));
    assert.equal(checkbox.checked, false);
    checkbox.checked = true;
    controls.find(n => n.type === 'checkbox' && n['aria-label']?.startsWith('Selecionar')).checked = true;
    page.get('pluggy-save').listeners.click();
    await flush();
    const request = page.calls.find(c => c.url.endsWith('review/'));
    assert.ok(request);
    const data = JSON.parse(request.options.body);
    assert.equal(data.action, 'create');
    assert.equal(data.revision, 2);
    assert.equal(data.project_remaining, true);
    assert.equal(data.distinct_purchase, false);
    assert.equal(data.posted_date, '2026-10-20');
    assert.equal(request.options.headers['X-CSRFToken'], 'csrf-test');
    assert.ok(page.calls.every(c => !c.url.startsWith('https://')));
});

test('suggestions initialize editable category, subcategory and description', async () => {
    const page = setup(row({ suggestion:{category_id:1, subcategory_id:2, description:'TC name'} }));
    await flush();
    const controls = page.get('pluggy-rows').all();
    assert.ok(controls.some(n=>n.tag==='input' && n.value==='TC name'));
    assert.ok(controls.some(n=>n.tag==='select' && n.value===1));
    assert.ok(controls.some(n=>n.tag==='select' && n.value===2));
});

test('new purchases start selected and dates display in Brazilian format', async () => {
    const page = setup(row());
    await flush();
    const controls = page.get('pluggy-rows').all();
    const chosen = controls.find(n => n['aria-label']?.startsWith('Selecionar'));
    assert.equal(chosen.checked, true);
    assert.equal(page.get('pluggy-checkall').checked, true);
    const date = controls.find(n => n.placeholder === 'dd/mm/aaaa');
    assert.equal(date.value, '20/10/2026');
    date.value = '31/02/2026';
    page.get('pluggy-save').listeners.click();
    await flush();
    assert.ok(page.get('pluggy-message').textContent.includes('data válida'));
    assert.ok(page.calls.every(c => !c.url.endsWith('review/')));
    date.value = '21/10/2026';
    page.get('pluggy-save').listeners.click();
    await flush();
    assert.equal(JSON.parse(page.calls.find(c => c.url.endsWith('review/')).options.body).posted_date, '2026-10-21');
});

test('unmapped purchases remain unchecked and options expand from the same row', async () => {
    const page = setup(row({ card_number: null }));
    await flush();
    const controls = page.get('pluggy-rows').all();
    const chosen = controls.find(n => n['aria-label']?.startsWith('Selecionar'));
    assert.equal(chosen.checked, false);
    assert.equal(chosen.disabled, true);
    const toggle = controls.find(n => n.tag === 'button' && n.title === 'Outras opções');
    const extra = controls.find(n => n.id === toggle['aria-controls']);
    assert.equal(extra.hidden, true);
    assert.ok(toggle.children.some(n => n.className === 'fa-solid fa-sliders'));
    assert.ok(controls.find(n => n.tag === 'tr' && n.children.some(td => td.children.includes(toggle))));
    toggle.listeners.click();
    assert.equal(extra.hidden, false);
    assert.equal(toggle['aria-expanded'], 'true');
    toggle.listeners.click();
    assert.equal(extra.hidden, true);
});

test('another import source does not trigger matching or classifier requests', async () => {
    const page = setup(row(), false);
    await flush();
    assert.equal(page.calls.length, 0);
    const choice = page.get('import-type-pluggy');
    choice.checked = true;
    choice.listeners.change();
    await flush();
    assert.equal(page.calls.length, 1);
    assert.ok(page.calls[0].url.endsWith('prepare/'));
});

test('visible candidate reconciles with one click without requiring classification', async () => {
    const page = setup(row({ matches:[{id:99,description:'Already renamed locally',posted_date:'2026-10-20',
        payment_date:'2026-11-10',value:'10.00',date_matches:true}] }));
    await flush();
    const controls = page.get('pluggy-rows').all();
    const reconcile = controls.find(n=>n.tag==='button' && n.textContent==='Conciliar');
    assert.ok(reconcile);
    const rows = page.get('pluggy-rows').children;
    const matchRow = rows.find(n => n.className === 'pluggy-match-row');
    assert.equal(matchRow.children[0].colSpan, 9);
    assert.ok(matchRow.all().includes(reconcile));
    assert.equal(matchRow.dataset.stripe, rows[rows.indexOf(matchRow) - 1].dataset.stripe);
    assert.ok(!rows[rows.indexOf(matchRow) - 1].all().includes(reconcile));
    assert.ok(controls.some(n=>n.textContent?.includes('Already renamed locally')));
    reconcile.listeners.click();
    await flush();
    const request = page.calls.find(call=>call.url.endsWith('review/'));
    const data = JSON.parse(request.options.body);
    assert.equal(data.action,'link');
    assert.equal(data.transaction_id,99);
    assert.equal(data.category_id,undefined);
});

test('select all skips candidates, but new purchase action selects one explicitly', async () => {
    const page = setup(row({ matches:[{id:99,description:'Possible existing purchase',posted_date:'2026-10-20',
        payment_date:'2026-11-10',value:'10.00',date_matches:true}] }));
    await flush();
    const controls = page.get('pluggy-rows').all();
    const selected = controls.find(n=>n.type==='checkbox' && n['aria-label']?.startsWith('Selecionar'));
    page.get('pluggy-checkall').listeners.change({target:{checked:true}});
    assert.equal(selected.checked,false);
    controls.find(n=>n.tag==='button' && n.textContent==='É uma nova compra').listeners.click();
    await flush();
    assert.equal(selected.checked,true);
    page.get('pluggy-save').listeners.click();
    await flush();
    const request = page.calls.find(call=>call.url.endsWith('review/'));
    assert.equal(JSON.parse(request.options.body).distinct_purchase,true);
});

test('original bill view renders source text and totals without requesting classification', async () => {
    const ledgerSource = await readFile(new URL('../../bank_sync/static/bank_sync/ledger.js', import.meta.url), 'utf8');
    const elements = new Map();
    const get = id => {
        if (!elements.has(id)) elements.set(id, new Element());
        return elements.get(id);
    };
    get('pluggy-ledger').dataset = {url:'/ledger/',reviewUrl:'/review/',importUrl:'/importar/'};
    const original = '<script>source bank text</script>';
    const payload = {selected_bill:'1',bills:[{id:'1',due_date:'2026-11-10',closing_date:'2026-11-03',total:'100.00',currency:'BRL',account:'Card'}],
        count:1, totals:{BRL:{charges:'100.00',refunds:'0.00',payments:'30.00',net:'100.00'}},
        groups:[{account:'Card',last_four:'1234',currency:'BRL',charges:'100.00',refunds:'0.00',payments:'30.00',net:'100.00',
            rows:[{id:1,revision:1,state:'imported',transaction_id:10,event:'purchase',
                facts:{description:original,payment_type:'SINGLE',date:'2026-11-01',amount:'100.00',currency:'BRL'}}]}]};
    const calls = [];
    const context = vm.createContext({URLSearchParams,window:{location:{search:''}},
        document:{getElementById:get,createElement:tag=>new Element(tag)},
        fetch:async(url)=>{calls.push(url);return {ok:true,json:async()=>payload};}});
    vm.runInContext(ledgerSource,context);
    await flush();
    assert.equal(calls.length,1);
    assert.ok(calls[0].startsWith('/ledger/'));
    assert.ok(get('ledger-groups').all().some(n=>n.tag==='td' && n.textContent===original));
    assert.ok(get('ledger-totals').all().some(n=>n.textContent?.includes('Total informado pelo banco')));
    assert.equal(get('ledger-import').href,'/importar/?fonte=pluggy&fatura=1');
});
