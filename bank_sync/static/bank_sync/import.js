const root = document.getElementById('pluggy-import');
const message = document.getElementById('pluggy-message');
const base = root.dataset.stateUrl.replace(/state\/$/, '');
let page = 1;
let payload;
let busy = false;
let selectedBill = new URLSearchParams(window.location.search).get('fatura') || '';
const editors = new Map();

function node(tag, text, parent) {
    const element = document.createElement(tag);
    if (text !== null) element.textContent = text;
    if (parent) parent.append(element);
    return element;
}
function button(parent, title, handler) {
    const element = node('button', title, parent);
    element.type = 'button';
    element.className = 'btn btn-default';
    element.addEventListener('click', () => work(handler));
    return element;
}
function select(parent, title, items, chosen = '') {
    const label = node('label', `${title} `, parent);
    label.style.margin = '8px';
    const element = node('select', null, label);
    element.className = 'form-control';
    items.forEach(([value, text]) => {
        const option = node('option', text, element);
        option.value = value;
    });
    element.value = chosen ?? '';
    return element;
}
function input(parent, title, value = '', type = 'text') {
    const label = node('label', `${title} `, parent);
    label.style.margin = '8px';
    const element = node('input', null, label);
    element.type = type;
    element.className = type === 'checkbox' ? '' : 'form-control';
    if (type === 'checkbox') element.checked = Boolean(value);
    else element.value = value;
    return element;
}
function amount(value, currency = 'BRL') {
    return value == null ? 'Não informado' : `${Number(value).toFixed(2)} ${currency}`;
}
function formatDate(value) {
    if (!value) return '';
    const [year, month, day] = value.slice(0, 10).split('-');
    return `${day}/${month}/${year}`;
}
function isoDate(value) {
    if (!value) return '';
    const match = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(value);
    if (!match) throw new Error('Informe a data no formato dd/mm/aaaa.');
    const [, day, month, year] = match;
    const iso = `${year}-${month}-${day}`;
    const date = new Date(`${iso}T12:00:00Z`);
    if (Number.isNaN(date.getTime()) || date.toISOString().slice(0, 10) !== iso) {
        throw new Error('Informe uma data válida no formato dd/mm/aaaa.');
    }
    return iso;
}
function dateInput(parent, title, value = '') {
    const field = input(parent, title, formatDate(value));
    field.placeholder = 'dd/mm/aaaa';
    field.inputMode = 'numeric';
    field.maxLength = 10;
    field.setAttribute('aria-label', title || 'Data da compra (dd/mm/aaaa)');
    return field;
}
function reconciliationMessage(result) {
    const count = result.reconciled_count || 1;
    const pending = result.remaining_installments || 0;
    return `${count} lançamento(s) conciliado(s). Os lançamentos existentes foram preservados.`
        + (pending ? ` ${pending} parcela(s) continuam pendentes por falta de correspondência única.` : '');
}
async function api(path, data) {
    const options = { credentials: 'same-origin', headers: { Accept: 'application/json' } };
    if (data) {
        options.method = 'POST';
        options.headers['Content-Type'] = 'application/json';
        options.headers['X-CSRFToken'] = root.querySelector('[name="csrfmiddlewaretoken"]').value;
        options.body = JSON.stringify(data);
    }
    const response = await fetch(base + path, options);
    if (!response.headers.get('content-type')?.includes('application/json')) {
        throw new Error('Sessão expirada ou resposta indisponível. Recarregue a página; depois consulte o resultado antes de repetir uma confirmação.');
    }
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || 'Operação não concluída.');
    return result;
}
async function work(handler) {
    if (busy) return;
    busy = true;
    root.setAttribute('aria-busy', 'true');
    message.textContent = 'Processando… aguarde. A consulta pode levar alguns minutos.';
    try {
        await handler();
        if (message.textContent.startsWith('Processando')) message.textContent = 'Concluído.';
    } catch (error) {
        message.textContent = error.message || 'Falha de conexão. Recarregue a revisão antes de repetir.';
    } finally {
        busy = false;
        root.setAttribute('aria-busy', 'false');
    }
}
async function load() {
    payload = await api('prepare/', { page, bill: selectedBill });
    page = payload.page;
    selectedBill = payload.selected_bill;
    render();
    message.textContent = payload.classifier_notice || 'Confira as candidatas e clique em Conciliar. Selecione apenas compras que deseja cadastrar como novas.';
}
function billLabel(bill) {
    const month = bill.due_date ? new Date(`${bill.due_date}T12:00:00`).toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' }) : 'Sem vencimento';
    return `${month} · ${bill.account} · ${formatDate(bill.due_date)}`;
}
function render() {
    const connections = document.getElementById('pluggy-connections');
    connections.replaceChildren();
    if (!payload.configured) {
        node('p', 'Conexão pessoal ainda não cadastrada no servidor. Execute sync_pluggy com o usuário proprietário, conforme o guia de configuração.', connections);
    }
    payload.connections.forEach((connection) => {
        const block = node('div', null, connections);
        node('p', `Última consulta: ${formatDate(connection.last_sync_at) || 'ainda não executada'}. Estado: ${connection.status || 'não consultado'}.`, block);
        if (connection.last_run?.state === 'failed') node('p', `Última consulta falhou: ${connection.last_run.message}`, block);
        if (connection.consent_expires_at) node('p', `Autorização válida até ${formatDate(connection.consent_expires_at)}.`, block);
        button(block, 'Consultar dados na Pluggy', async () => {
            await api('sync/', { connection_id: connection.id });
            await load();
        });
    });
    renderMappings();
    const bills = document.getElementById('pluggy-bill');
    bills.replaceChildren();
    [...payload.bills.map((bill) => [bill.id, billLabel(bill)]), ['unbilled', 'Sem fatura definida'], ['all', 'Todas as faturas']].forEach(([value, title]) => {
        const option = node('option', title, bills);
        option.value = value;
    });
    bills.value = selectedBill;
    document.getElementById('pluggy-page').textContent = `${payload.count} ocorrências · página ${payload.page}/${payload.pages}`;
    document.getElementById('pluggy-prev').disabled = page <= 1;
    document.getElementById('pluggy-next').disabled = page >= payload.pages;
    const rows = document.getElementById('pluggy-rows');
    rows.replaceChildren();
    editors.clear();
    const groups = new Map();
    payload.rows.forEach((row) => {
        const key = `${row.account_id}:${row.facts.last_four || 'unknown'}`;
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(row);
    });
    for (const group of groups.values()) {
        const header = node('tr', null, rows);
        header.className = 'group-header';
        const cell = node('td', group[0].card_number?.name || `Cartão não identificado · final ${group[0].facts.last_four || 'ausente'}`, header);
        cell.colSpan = 9;
        group.forEach((row) => renderRow(rows, row));
    }
    if (!payload.rows.length) {
        const row = node('tr', null, rows);
        node('td', 'Nenhuma compra pendente de importação nesta fatura.', row).colSpan = 9;
    }
    updateCheckAll();

}
function renderMappings() {
    const parent = document.getElementById('pluggy-mappings');
    parent.replaceChildren();
    payload.accounts.forEach((account) => {
        const block = node('div', null, parent);
        node('h4', account.name, block);
        if (account.edit_card_url) {
            const edit = node('a', 'Cadastrar ou conferir números deste cartão', block);
            edit.href = account.edit_card_url;
            edit.target = '_blank';
            edit.rel = 'noopener';
        }
        const cards = select(block, 'Cartão/fatura local', [['', 'Selecione'], ...payload.cards.map((c) => [c.id, c.description])], account.card_id);
        const aliases = node('div', null, block);
        let fields = [];
        function populate() {
            aliases.replaceChildren();
            fields = account.identifiers.map((alias) => [alias.last_four, select(aliases, `Final ${alias.last_four}`, [
                ['', 'Não identificado / buscar final correspondente ao salvar'],
                ...payload.card_numbers.filter((n) => String(n.card_id) === cards.value).map((n) => [n.id, n.name]),
            ], alias.card_number_id)]);
        }
        cards.addEventListener('change', populate);
        populate();
        button(block, 'Salvar vínculos', async () => {
            await api('map/', { account_id: account.id, card_id: cards.value,
                aliases: Object.fromEntries(fields.map(([final, field]) => [final, field.value])) });
            await load();
        });
    });
}
function renderRow(parent, row) {
    const facts = row.facts;
    const suggestion = row.suggestion || {};
    const tr = node('tr', null, parent);
    tr.className = 'row-disabled';
    const stripe = editors.size % 2 === 0 ? 'odd' : 'even';
    tr.dataset.stripe = stripe;
    function cell(className) {
        const td = node('td', null, tr);
        td.className = className;
        return td;
    }
    const chosen = input(cell('import-col-check'), '', false, 'checkbox');
    chosen.setAttribute('aria-label', `Selecionar ${facts.description}`);
    const allowed = Boolean(row.card_number && row.event === 'purchase' && facts.currency === 'BRL' && ['SINGLE', 'INSTALLMENT'].includes(facts.payment_type));
    chosen.disabled = !allowed;
    chosen.checked = allowed && !row.matches?.length;
    tr.classList.toggle('row-disabled', !chosen.checked);
    chosen.addEventListener('change', () => {
        tr.classList.toggle('row-disabled', !chosen.checked);
        updateCheckAll();
    });
    const posted = dateInput(cell('import-col-date'), '', facts.purchase_date || facts.date);
    const parcel = cell('import-col-installment');
    parcel.textContent = facts.payment_type === 'INSTALLMENT' ? `${facts.number}/${facts.total}` : 'À vista';
    const category = select(cell('import-col-category'), '', [['', 'Selecione'], ...payload.categories.filter((c) => c.type === 'saida').map((c) => [c.id, c.description])], suggestion.category_id);
    const subcategory = select(cell('import-col-subcategory'), '', [['', 'Selecione']]);
    const descriptionCell = cell('import-col-description');
    const description = input(descriptionCell, '', suggestion.description || facts.description);
    description.title = `Original: ${facts.description}`;
    const value = input(cell('import-col-value'), '', facts.amount, 'number');
    value.step = '0.01';
    value.min = '0.01';
    const event = cell('import-col-event-type');
    event.textContent = ({purchase:'Compra',card_payment:'Pagamento da fatura',refund:'Estorno/crédito',unknown:'Revisar evento'})[row.event] || 'Revisar evento';
    event.title = `${facts.status} · vencimento ${formatDate(row.due_date) || 'a confirmar'}`;
    if (!allowed) event.title += ` · ${!row.card_number ? 'Identifique o cartão para cadastrar.' : 'Vincule ao cadastro financeiro revisado ou ignore.'}`;
    function subcategories(selected = '') {
        subcategory.replaceChildren();
        [['', 'Selecione'], ...payload.subcategories.filter((s) => String(s.category_id) === String(category.value)).map((s) => [s.id, s.description])].forEach(([id, title]) => {
            const option = node('option', title, subcategory);
            option.value = id;
        });
        subcategory.value = selected ?? '';
    }
    category.addEventListener('change', () => subcategories());
    subcategories(suggestion.subcategory_id);
    const matchRow = row.matches?.length ? node('tr', null, parent) : null;
    if (matchRow) {
        matchRow.className = 'pluggy-match-row';
        matchRow.dataset.stripe = stripe;
    }
    const matchCell = matchRow ? node('td', null, matchRow) : null;
    if (matchCell) matchCell.colSpan = 9;
    const extra = node('tr', null, parent);
    extra.hidden = true;
    extra.className = 'pluggy-expanded-row';
    extra.dataset.stripe = stripe;
    const extraCell = node('td', null, extra);
    extraCell.colSpan = 9;
    const optionsButton = node('button', null, cell('pluggy-col-options'));
    optionsButton.type = 'button';
    optionsButton.className = 'btn btn-default';
    optionsButton.title = 'Outras opções';
    optionsButton.setAttribute('aria-label', 'Outras opções');
    optionsButton.setAttribute('aria-expanded', 'false');
    extra.id = `pluggy-options-${row.id}`;
    optionsButton.setAttribute('aria-controls', extra.id);
    const icon = node('i', null, optionsButton);
    icon.className = 'fa-solid fa-sliders';
    icon.setAttribute('aria-hidden', 'true');
    optionsButton.addEventListener('click', () => {
        extra.hidden = !extra.hidden;
        optionsButton.setAttribute('aria-expanded', String(!extra.hidden));
    });
    if (row.matches?.length) {
        const matchPanel = node('div', null, matchCell);
        matchPanel.className = 'pluggy-matches';
        node('strong', row.matches.length === 1 ? 'Provável correspondência' : 'Escolha a correspondência correta', matchPanel);
        for (const match of row.matches) {
            const item = node('div', null, matchPanel);
            item.className = 'pluggy-match';
            const reason = match.date_matches ? 'Mesma data e valor' : 'Mesmo valor nesta fatura';
            const comparison = node('div', null, item);
            node('span', `${reason} · ${match.description} · ${amount(match.value)}`, comparison);
            const installment = match.total ? ` · parcela ${match.number}/${match.total}` : '';
            comparison.title = `Compra: ${formatDate(match.posted_date) || 'não informada'} · vencimento: ${formatDate(match.payment_date)}${installment}`;
            const reconcile = button(item, 'Conciliar', async () => {
                const result = await api('review/', { id: row.id, revision: row.revision, action: 'link', transaction_id: match.id,
                    payment_date: row.due_date || match.payment_date, confirm_estimate: !row.due_date });
                await load();
                message.textContent = reconciliationMessage(result);
            });
            reconcile.disabled = !row.card_number;
            reconcile.title = !row.card_number ? 'Identifique o cartão primeiro.' : `Conciliar com o lançamento #${match.id}${facts.payment_type === 'INSTALLMENT' ? ' e as demais parcelas correspondentes desta compra, em todas as faturas' : ''}`;
        }
        button(matchPanel, 'É uma nova compra', async () => {
            chosen.checked = true;
            tr.classList.remove('row-disabled');
            updateCheckAll();
            message.textContent = 'Compra selecionada para cadastrar como nova. Confira os campos e clique em Cadastrar selecionados.';
        }).disabled = !allowed;
    }
    const details = node('div', null, extraCell);
    details.className = 'pluggy-options';
    const paymentDate = row.due_date ? null : dateInput(details, 'Vencimento estimado');
    const estimate = row.due_date ? null : input(details, 'Confirmo a data estimada', false, 'checkbox');
    const project = facts.payment_type === 'INSTALLMENT' ? input(details, 'Projetar parcelas restantes ausentes (estimativa revisável)', false, 'checkbox') : null;
    const target = input(details, 'ID do lançamento existente', '', 'number');
    const candidates = node('div', null, details);
    button(details, 'Buscar outros lançamentos semelhantes', async () => {
        const result = await api(`details/${row.id}/`);
        candidates.replaceChildren();
        for (const match of result.candidates) button(candidates, `Selecionar #${match.id}: ${match.description} · ${amount(match.value)}`, async () => { target.value = match.id; });
        if (!result.candidates.length) node('p', 'Nenhum candidato. Você pode informar um ID manualmente.', candidates);
    });
    async function link() {
        const result = await api('review/', { id: row.id, revision: row.revision, action: 'link', transaction_id: target.value,
            payment_date: paymentDate ? isoDate(paymentDate.value) : undefined, confirm_estimate: estimate?.checked || false });
        await load();
        message.textContent = reconciliationMessage(result);
    }
    button(details, 'Vincular ao lançamento existente', link);
    button(details, 'Atualizar sugestão do TC', async () => {
        const result = await api('predict/', { id: row.id });
        category.value = result.category_id || '';
        subcategories(result.subcategory_id);
        description.value = result.description || facts.description;
    });
    button(details, 'Ignorar esta ocorrência', async () => {
        await api('review/', { id: row.id, revision: row.revision, action: 'ignore' });
        await load();
    });
    function data() {
        return { id: row.id, revision: row.revision, action: 'create', category_id: category.value,
            subcategory_id: subcategory.value, description: description.value, posted_date: isoDate(posted.value),
            value: value.value, payment_date: paymentDate ? isoDate(paymentDate.value) : undefined, confirm_estimate: estimate?.checked || false,
            distinct_purchase: Boolean(row.matches?.length && chosen.checked), project_remaining: project?.checked || false };
    }
    editors.set(row.id, { chosen, tr, extra, data, hasMatches: Boolean(row.matches?.length) });
}
function updateCheckAll() {
    const checkboxes = [...editors.values()].filter((editor) => !editor.hasMatches).map((editor) => editor.chosen).filter((box) => !box.disabled);
    const selected = checkboxes.filter((box) => box.checked).length;
    const all = document.getElementById('pluggy-checkall');
    all.checked = checkboxes.length > 0 && selected === checkboxes.length;
    all.indeterminate = selected > 0 && selected < checkboxes.length;
}
async function saveSelected() {
    const selected = [...editors.values()].filter((editor) => editor.chosen.checked && !editor.chosen.disabled);
    if (!selected.length) throw new Error('Selecione as compras que deseja cadastrar.');
    let saved = 0;
    for (const editor of selected) {
        try {
            await api('review/', editor.data());
            editor.chosen.checked = false;
            editor.chosen.disabled = true;
            editor.tr.classList.add('row-disabled');
            saved++;
        } catch (error) {
            updateCheckAll();
            throw new Error(`${saved} compra(s) cadastrada(s). As demais edições foram preservadas. ${error.message}`);
        }
    }
    await load();
    message.textContent = `${saved} compra(s) cadastrada(s).`;
}
document.getElementById('pluggy-refresh').addEventListener('click', () => work(load));
document.getElementById('pluggy-bill').addEventListener('change', (event) => { page = 1; selectedBill = event.target.value; work(load); });
document.getElementById('pluggy-prev').addEventListener('click', () => { if (page > 1) { page--; work(load); } });
document.getElementById('pluggy-next').addEventListener('click', () => { if (page < payload.pages) { page++; work(load); } });
document.getElementById('pluggy-checkall').addEventListener('change', (event) => {
    for (const editor of editors.values()) {
        if (!editor.chosen.disabled && !editor.hasMatches) {
            editor.chosen.checked = event.target.checked;
            editor.tr.classList.toggle('row-disabled', !event.target.checked);
        }
    }
    updateCheckAll();
});
document.getElementById('pluggy-save').addEventListener('click', () => work(saveSelected));
const pluggyChoice = document.getElementById('import-type-pluggy');
pluggyChoice?.addEventListener('change', () => { if (pluggyChoice.checked && !payload) work(load); });
if (!pluggyChoice || pluggyChoice.checked) work(load);
