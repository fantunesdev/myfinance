const byId = id => document.getElementById(id);
const list = byId('investment-events');
const state = byId('event-state');
const token = document.querySelector('[name=csrfmiddlewaretoken]').value;
const money = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
const labels = { new: 'Novo', historical: 'Histórico a conferir', conflict: 'Fonte alterada', linked: 'Vinculado', applied: 'Conciliado', ignored: 'Ignorado' };
const kinds = { buy: 'Compra', sell: 'Venda ou resgate', income: 'Provento', tax: 'Tributo', transfer: 'Transferência', amortization: 'Amortização', ambiguous: 'Natureza a conferir' };
const sourceKinds = { BUY: 'Compra', SELL: 'Venda ou resgate', INTEREST: 'Provento', TAX: 'Tributo', TRANSFER: 'Transferência', AMORTIZATION: 'Amortização' };
const movementKinds = { aporte: 'Aporte/aplicação', resgate: 'Resgate', rendimento: 'Rendimento', custo: 'Taxa/imposto', atualizacao: 'Avaliação' };
const pendingStates = new Set(['new', 'historical', 'conflict']);
const selected = new Map();
const contexts = new Map();
let page = 1;
let requestNumber = 0;
let poll;
let signature = '';
let stale = false;

function el(tag, text, className) {
    const element = document.createElement(tag);
    if (text !== undefined) element.textContent = text;
    if (className) element.className = className;
    return element;
}
function date(value) {
    const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(value || ''));
    return match ? `${match[3]}/${match[2]}/${match[1]}` : 'Data a conferir';
}
function amount(value, absolute = false) {
    if (value === null || value === undefined || value === '' || !Number.isFinite(Number(value))) return 'Valor a conferir';
    return money.format(absolute ? Math.abs(Number(value)) : Number(value));
}
function feedback(message, error = false) {
    const target = byId('event-action-status');
    target.textContent = message;
    target.dataset.error = String(error);
    target.hidden = !message;
}
async function jsonResponse(response) {
    if (!(response.headers.get('content-type') || '').includes('application/json')) {
        const error = Error('Entre novamente para continuar.');
        error.auth = true;
        throw error;
    }
    const data = await response.json();
    if (!response.ok) {
        const error = Error(data.detail || 'Não foi possível concluir a operação.');
        error.auth = [401, 403].includes(response.status);
        throw error;
    }
    return data;
}
async function post(url, data) {
    return jsonResponse(await fetch(url, { method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': token }, body: JSON.stringify(data) }));
}
function field(id, label, control) {
    const wrapper = el('div', undefined, 'reconciliation-field');
    control.id = id;
    const caption = el('label', label);
    caption.htmlFor = id;
    wrapper.append(caption, control);
    return wrapper;
}
function choices(options) {
    const select = el('select');
    for (const [value, label] of options) {
        const option = el('option', label);
        option.value = value;
        select.append(option);
    }
    return select;
}
function section() { return el('fieldset'); }
function show(section, visible) { section.hidden = !visible; section.disabled = !visible; }
function numeric() {
    const input = el('input');
    input.type = 'number'; input.min = '0.01'; input.step = '0.01';
    return input;
}
function reviewOpen() { return Boolean(list.querySelector('details[data-review][open]')); }
function clearSelection() {
    selected.clear();
    for (const input of list.querySelectorAll('.group-event')) input.checked = false;
    updateSelection();
}
function updateSelection() {
    byId('event-selection').hidden = selected.size === 0;
    const transfer = [...selected.values()][0]?.kind === 'transfer';
    byId('selected-count').textContent = transfer
        ? `${selected.size} ponta(s) selecionada(s). Selecione origem e destino da transferência.`
        : `${selected.size} compra(s) selecionada(s). Use uma das selecionadas para confirmar a liquidação conjunta.`;
    for (const context of contexts.values()) context.refresh();
}
function facts(event, body) {
    const details = el('details', undefined, 'reconciliation-facts');
    details.append(el('summary', 'Dados recebidos da instituição'));
    const entries = [
        ['Data', date(event.facts.tradeDate || event.facts.date)],
        ['Tipo na instituição', sourceKinds[event.facts.type] || 'A conferir'],
        ['Valor informado', amount(event.facts.amount)],
        ['Valor líquido', amount(event.facts.netAmount)],
    ];
    if (event.facts.type === 'TRANSFER' && event.facts.movementType) entries.push(['Sentido', event.facts.movementType === 'DEBIT' ? 'Saída' : 'Entrada']);
    if (event.facts.quantity !== null && event.facts.quantity !== undefined) entries.push(['Quantidade', String(event.facts.quantity)]);
    if (event.facts.description) entries.push(['Descrição', event.facts.description]);
    const definition = el('dl');
    for (const [label, value] of entries) definition.append(el('dt', label), el('dd', value));
    details.append(definition); body.append(details);
}
function resolvedDetails(event, body) {
    const descriptions = {
        applied: 'Evento conferido e registrado. Nenhuma ação adicional é necessária.',
        linked: 'Evento vinculado aos lançamentos existentes. Nenhuma ação adicional é necessária.',
        ignored: 'Evento ignorado com justificativa.',
    };
    body.append(el('p', descriptions[event.state] || 'Evento concluído.'));
    if (event.state === 'ignored' && event.reason) body.append(el('p', event.reason, 'reconciliation-help'));
    if (event.operation?.event_count > 1) body.append(el('p', `Esta conciliação reúne ${event.operation.event_count} eventos. Os lançamentos e comprovantes abaixo correspondem ao conjunto.`, 'reconciliation-help'));
    if (event.matched_movements?.length) {
        body.append(el('h5', 'Lançamentos vinculados'));
        const records = el('ul', undefined, 'reconciliation-records');
        for (const movement of event.matched_movements) {
            records.append(el('li', `${date(movement.date)} · ${movementKinds[movement.type] || movement.type} · ${amount(movement.type === 'atualizacao' ? movement.current_value : movement.amount)} · ${movement.investment}`));
        }
        body.append(records);
    }
    if (event.settlements?.length) {
        body.append(el('h5', 'Comprovado na conta bancária'));
        const records = el('ul', undefined, 'reconciliation-records');
        for (const settlement of event.settlements) {
            const f = settlement.facts;
            records.append(el('li', `${date(f.date)} · ${f.type === 'DEBIT' ? 'Débito' : 'Crédito'} de ${amount(f.amount, true)} · ${f.description || 'Movimentação bancária'}`));
        }
        body.append(records);
    }
    facts(event, body);
}
function reviewForm(event, body, data, details) {
    if (event.state === 'historical') body.append(el('p', 'Este evento é anterior ao saldo conciliado. Vincule-o a um registro existente para evitar uma nova aplicação sobre o mesmo dinheiro.', 'reconciliation-help'));
    else if (event.state === 'conflict') {
        body.append(el('p', 'A instituição alterou um evento já conferido. Compare os dados e os lançamentos antes de manter os registros atuais.', 'reconciliation-help'));
        if (event.reason) body.append(el('p', event.reason, 'reconciliation-help'));
        if (event.matched_movements?.length) {
            const records = el('ul', undefined, 'reconciliation-records');
            for (const m of event.matched_movements) records.append(el('li', `${date(m.date)} · ${movementKinds[m.type] || m.type} · ${amount(m.type === 'atualizacao' ? m.current_value : m.amount)} · ${m.investment}`));
            body.append(records);
        }
    } else if (event.reason) body.append(el('p', event.reason, 'reconciliation-help'));
    facts(event, body);
    const form = el('form', undefined, 'reconciliation-form');
    const key = `event-${event.id}`;
    const actions = event.state === 'conflict' ? [['keep', 'Manter os registros atuais']]
        : event.state === 'historical' ? [['link', 'Vincular a um lançamento existente'], ['ignore', 'Ignorar com justificativa']]
        : [['link', 'Vincular a um lançamento existente'], ['apply', 'Registrar operação'], ['ignore', 'Ignorar com justificativa']];
    const action = choices(actions);
    if (event.state === 'new' && !event.candidates.length && event.mapped !== false) action.value = 'apply';
    form.append(field(`${key}-action`, 'Como deseja resolver?', action));
    const existingSection = section();
    const existing = choices(event.candidates.map(m => [String(m.id), `${date(m.date)} · ${movementKinds[m.type] || m.type} · ${amount(m.amount)}${m.description ? ` · ${m.description.slice(0, 80)}` : ''}`]));
    existing.multiple = true; existing.required = true; existing.size = Math.min(5, Math.max(2, event.candidates.length));
    existingSection.append(field(`${key}-existing`, 'Lançamentos do MyFinance', existing));
    if (!event.candidates.length) existingSection.append(el('p', 'Não há lançamentos próximos a esta data para vincular.', 'reconciliation-help'));
    form.append(existingSection);
    const classificationSection = section();
    const classificationOptions = [['', 'Selecione a natureza comprovada'], ['income', 'Provento recebido']];
    if (Number(event.facts.quantity) > 0) classificationOptions.push(['sell', 'Venda com quantidade comprovada']);
    const classification = choices(classificationOptions);
    classification.required = true;
    classificationSection.append(field(`${key}-kind`, 'O que este evento representa?', classification)); form.append(classificationSection);
    const cashSection = section();
    const cash = choices(event.cash_candidates.map(c => [String(c.id), `${date(c.facts.date)} · ${c.facts.type === 'DEBIT' ? 'Débito' : 'Crédito'} ${amount(c.facts.amount, true)} · ${c.facts.description || 'Movimentação bancária'}`]));
    cash.multiple = true; cash.required = true; cash.size = Math.min(5, Math.max(2, event.cash_candidates.length));
    cashSection.append(field(`${key}-cash`, 'Liquidação na conta bancária', cash));
    if (!event.cash_candidates.length) cashSection.append(el('p', 'Não há liquidações disponíveis nessa data. Consulte a Pluggy antes de registrar a operação.', 'reconciliation-help'));
    form.append(cashSection);
    const principalSection = section();
    const principal = numeric(); principal.required = true;
    principalSection.append(field(`${key}-principal`, 'Custo comprovado da parcela vendida ou transferida (R$)', principal)); form.append(principalSection);
    const fundingSection = section();
    fundingSection.append(el('h5', 'De onde saiu o dinheiro?'), el('p', 'Distribua o valor do débito entre as entradas de caixa utilizadas.', 'reconciliation-help'));
    const allocationRows = el('div');
    const available = data.credits.filter(c => c.date <= (event.facts.tradeDate || event.facts.date).slice(0, 10));
    let allocationNumber = 0;
    function addAllocation() {
        const index = allocationNumber++;
        const row = el('div', undefined, 'reconciliation-allocation');
        const credit = choices([['', 'Selecione uma entrada'], ...available.map(c => [String(c.id), `${date(c.date)} · ${amount(c.available)} disponíveis${c.notes ? ` · ${c.notes.slice(0, 65)}` : ''}`])]);
        credit.required = true; credit.dataset.credit = 'true';
        const value = numeric(); value.required = true; value.dataset.amount = 'true';
        credit.addEventListener('change', () => { value.max = available.find(c => String(c.id) === credit.value)?.available || ''; });
        const remove = el('button', 'Remover', 'reconciliation-link'); remove.type = 'button';
        remove.addEventListener('click', () => row.remove());
        row.append(field(`${key}-credit-${index}`, 'Entrada de origem', credit), field(`${key}-amount-${index}`, 'Valor utilizado (R$)', value), remove);
        allocationRows.append(row);
    }
    const addOrigin = el('button', 'Adicionar origem', 'reconciliation-link'); addOrigin.type = 'button';
    addOrigin.addEventListener('click', addAllocation);
    if (available.length) addAllocation();
    else fundingSection.append(el('p', 'Não há crédito de caixa elegível até esta data. Confira a entrada de origem antes de aplicar.', 'reconciliation-help'));
    fundingSection.append(allocationRows, addOrigin); form.append(fundingSection);
    const feeSection = section();
    const sharedCost = numeric(); sharedCost.min = '0'; sharedCost.value = '0';
    feeSection.append(field(`${key}-fee`, 'Custo adicional comprovado da nota conjunta (R$)', sharedCost)); form.append(feeSection);
    const evidence = el('textarea'); evidence.required = true;
    evidence.placeholder = 'Descreva a correspondência com o extrato ou o motivo da decisão.';
    form.append(field(`${key}-evidence`, 'Justificativa da conferência', evidence));
    const groupHint = el('p', undefined, 'reconciliation-help'); form.append(groupHint);
    const buttons = el('div', undefined, 'reconciliation-form-actions');
    const submit = el('button', 'Confirmar', 'btn btn-primary'); submit.type = 'submit';
    const cancel = el('button', 'Fechar revisão', 'reconciliation-link'); cancel.type = 'button';
    cancel.addEventListener('click', () => { details.open = false; });
    buttons.append(submit, cancel); form.append(buttons);
    let submitting = false;
    const refresh = () => {
        const applying = action.value === 'apply';
        const kind = classification.value || event.kind;
        const grouped = selected.has(event.id) && selected.size > 1;
        const transfer = kind === 'transfer';
        show(existingSection, action.value === 'link');
        show(classificationSection, applying && (event.source_kind || event.kind) === 'ambiguous');
        show(cashSection, applying && !transfer);
        show(principalSection, applying && ['sell', 'transfer'].includes(kind));
        show(fundingSection, applying && ['buy', 'tax'].includes(kind));
        show(feeSection, applying && kind === 'buy' && grouped);
        groupHint.hidden = !applying || !transfer;
        groupHint.textContent = 'Selecione as duas pontas da transferência para registrar a operação conjunta.';
        submit.disabled = submitting || (applying && transfer && !grouped) || (event.mapped === false && !['ignore', 'keep'].includes(action.value));
        submit.textContent = { link: 'Vincular lançamento', apply: grouped ? `Confirmar ${selected.size} eventos selecionados` : 'Registrar operação', ignore: 'Ignorar evento', keep: 'Manter registros atuais' }[action.value];
    };
    contexts.set(event.id, { refresh, action });
    action.addEventListener('change', refresh); classification.addEventListener('change', refresh);
    if (event.state === 'new' && ['buy', 'transfer'].includes(event.kind) && event.mapped !== false) {
        const group = el('label', undefined, 'reconciliation-group');
        const input = el('input'); input.type = 'checkbox'; input.className = 'group-event'; input.dataset.id = event.id;
        group.append(input, el('span', event.kind === 'buy' ? 'Agrupar com outras compras da mesma liquidação' : 'Selecionar esta ponta de uma transferência'));
        input.addEventListener('change', () => {
            if (input.checked) {
                if (selected.size && [...selected.values()][0].kind !== event.kind) {
                    input.checked = false; feedback('Agrupe apenas eventos da mesma natureza.', true); return;
                }
                selected.set(event.id, event); action.value = 'apply';
            } else selected.delete(event.id);
            updateSelection();
        });
        body.append(group);
    }
    if (event.mapped === false) body.append(el('p', 'O investimento ainda precisa ser associado ao cadastro correto antes de vincular ou registrar a operação.', 'reconciliation-help'));
    form.addEventListener('submit', async e => {
        e.preventDefault();
        if (submitting) return;
        submitting = true; submit.disabled = true;
        try {
            const grouped = action.value === 'apply' && selected.has(event.id) && selected.size > 1;
            const allocations = !fundingSection.hidden ? [...allocationRows.children].map(row => ({ credit_id: Number(row.querySelector('[data-credit]').value), amount: row.querySelector('[data-amount]').value })) : [];
            if (new Set(allocations.map(a => a.credit_id)).size !== allocations.length) throw Error('Selecione cada entrada de origem uma única vez.');
            await post(`${list.dataset.reviewBase}${event.id}/`, {
                revision: event.revision, action: action.value, evidence: evidence.value,
                events: grouped ? [...selected.values()].map(item => ({ id: item.id, revision: item.revision })) : [],
                movement_ids: !existingSection.hidden ? [...existing.selectedOptions].map(o => Number(o.value)) : [],
                cash_ids: !cashSection.hidden ? [...cash.selectedOptions].map(o => Number(o.value)) : [],
                allocations, principal: !principalSection.hidden ? principal.value : null,
                kind: !classificationSection.hidden ? classification.value : null,
                shared_cost: !feeSection.hidden ? sharedCost.value || '0' : '0',
            });
            feedback('Conciliação registrada.'); clearSelection();
            await load(true);
        } catch (error) { feedback(error.message, true); }
        finally { submitting = false; refresh(); }
    });
    body.append(form); refresh();
}
function eventRow(event, data) {
    const details = el('details', undefined, 'reconciliation-event');
    if (pendingStates.has(event.state)) details.dataset.review = 'true';
    const summary = el('summary');
    const description = el('span', undefined, 'reconciliation-event-description');
    description.append(el('strong', event.titles.join(', ') || 'Investimento a identificar', 'reconciliation-event-title'), el('span', kinds[event.kind] || 'Natureza a conferir', 'reconciliation-event-kind'));
    const badge = el('span', labels[event.state] || 'A conferir', 'reconciliation-badge'); badge.dataset.state = event.state;
    summary.append(el('span', date(event.facts.tradeDate || event.facts.date), 'reconciliation-event-date'), description,
        el('strong', amount(event.facts.netAmount ?? event.facts.amount), 'reconciliation-event-amount'), badge);
    const body = el('div', undefined, 'reconciliation-event-body');
    let built = false;
    details.addEventListener('toggle', () => {
        if (details.open && !built) {
            built = true;
            if (pendingStates.has(event.state)) reviewForm(event, body, data, details);
            else resolvedDetails(event, body);
        }
        if (!details.open && stale && !reviewOpen()) load(true);
    });
    details.append(summary, body); return details;
}
function collectionStatus(jobs) {
    const running = jobs.find(j => ['queued', 'running'].includes(j.state));
    byId('history-collect').disabled = Boolean(running);
    let text = '';
    if (running) {
        text = running.state === 'queued' ? 'Consulta aguardando início…' : running.progress.total_titles
            ? `Consultando ${running.progress.titles || 0} de ${running.progress.total_titles} investimentos…` : 'Consultando movimentações…';
    } else if (jobs[0]?.state === 'failed') text = 'A última consulta não foi concluída. Tente novamente.';
    else if (jobs[0]?.finished_at) {
        const finished = new Date(jobs[0].finished_at);
        text = Number.isNaN(finished.getTime()) ? 'Última consulta concluída.' : `Última consulta: ${finished.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })}.`;
    }
    byId('history-status').textContent = text;
    return Boolean(running);
}
async function load(force = false) {
    const request = ++requestNumber;
    clearTimeout(poll); list.setAttribute('aria-busy', 'true');
    try {
        const response = await fetch(`${list.dataset.url}?page=${page}&state=${encodeURIComponent(state.value)}`, { credentials: 'same-origin' });
        const data = await jsonResponse(response);
        if (request !== requestNumber) return;
        page = data.page;
        byId('pending-count').textContent = data.summary.pending;
        byId('resolved-count').textContent = data.summary.resolved;
        const running = collectionStatus(data.jobs);
        const nextSignature = JSON.stringify([state.value, page, data.events, data.credits]);
        if (force || !reviewOpen() || signature === nextSignature) {
            if (force || signature !== nextSignature) {
                selected.clear(); contexts.clear(); updateSelection();
                list.replaceChildren(...data.events.map(event => eventRow(event, data)));
                signature = nextSignature;
            }
            stale = false;
        } else stale = true;
        byId('event-updates').hidden = !stale;
        const empty = data.count === 0;
        byId('event-empty').hidden = !empty || stale;
        const pending = state.value === 'pending';
        byId('empty-title').textContent = pending && data.summary.total ? 'Nenhum evento precisa de revisão' : pending ? 'Nenhuma movimentação consultada' : 'Histórico vazio';
        byId('empty-description').textContent = pending && data.summary.resolved
            ? `${data.summary.resolved} eventos concluídos estão disponíveis no histórico.`
            : pending ? 'Consulte a Pluggy para buscar movimentações dos seus investimentos.' : 'Os eventos aparecerão aqui depois de serem conciliados ou ignorados.';
        byId('show-history').hidden = !pending || !data.summary.resolved;
        byId('empty-icon').textContent = pending && data.summary.total ? '✓' : '—';
        byId('event-help').hidden = empty || stale;
        byId('event-help').textContent = pending ? 'Abra um evento para conferir e resolver a pendência.' : 'Eventos concluídos ficam disponíveis para consulta e não exigem outra ação.';
        byId('event-pagination').hidden = data.pages <= 1 || stale;
        byId('previous-page').disabled = page <= 1;
        byId('next-page').disabled = page >= data.pages;
        byId('page-label').textContent = `${page} de ${data.pages}`;
        byId('event-count').textContent = empty ? '' : `Mostrando ${(page - 1) * data.page_size + 1}–${Math.min(page * data.page_size, data.count)} de ${data.count} eventos ${pending ? 'a revisar' : 'concluídos'}.`;
        if (running) poll = setTimeout(() => load(), 3000);
    } catch (error) {
        if (request !== requestNumber) return;
        feedback(error.message, true);
        if (error.auth) {
            list.replaceChildren(); byId('event-empty').hidden = true;
            byId('pending-count').textContent = '—'; byId('resolved-count').textContent = '—';
            selected.clear(); contexts.clear(); updateSelection();
        }
    } finally { if (request === requestNumber) list.setAttribute('aria-busy', 'false'); }
}
function changeView(view) {
    state.value = view; page = 1; signature = ''; stale = false;
    clearSelection(); feedback('');
    for (const button of document.querySelectorAll('[data-view]')) button.setAttribute('aria-pressed', String(button.dataset.view === view));
    load(true);
}
for (const button of document.querySelectorAll('[data-view]')) button.addEventListener('click', () => changeView(button.dataset.view));
byId('show-history').addEventListener('click', () => changeView('resolved'));
byId('clear-selection').addEventListener('click', clearSelection);
byId('history-job').addEventListener('submit', async event => {
    event.preventDefault(); byId('history-collect').disabled = true; feedback('');
    try { await post(event.currentTarget.action, {}); await load(); }
    catch (error) { feedback(error.message, true); byId('history-collect').disabled = false; }
});
byId('previous-page').addEventListener('click', () => { page--; clearSelection(); load(true); });
byId('next-page').addEventListener('click', () => { page++; clearSelection(); load(true); });
load();
