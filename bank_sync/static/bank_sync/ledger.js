const root = document.getElementById('pluggy-ledger');
const select = document.getElementById('ledger-bill');
const message = document.getElementById('ledger-message');
let busy = false;
const pdfButton = document.getElementById('ledger-pdf');
const cardChoices = new Map();
pdfButton.addEventListener('click', () => {
    if (!busy && !pdfButton.disabled) window.location.assign(pdfButton.dataset.downloadUrl);
});
const labels = {new:'Pendente de conciliação', imported:'Importado', linked:'Conciliado', ignored:'Ignorado', conflict:'Alteração para revisar'};
function node(tag, text, parent) {
    const element = document.createElement(tag);
    if (text !== null) element.textContent = text;
    if (parent) parent.append(element);
    return element;
}
function amount(value, currency = 'BRL') {
    return new Intl.NumberFormat('pt-BR', { style:'currency', currency }).format(Number(value || 0));
}
function date(value) {
    return value ? value.slice(0,10).split('-').reverse().join('/') : 'Não informado';
}
async function review(row, action) {
    if (!window.confirm(action === 'unlink' ? 'Desfazer o vínculo e preservar o lançamento local?' : 'Você revisou e deseja manter o lançamento local?')) return;
    const response = await fetch(root.dataset.reviewUrl, { method:'POST', credentials:'same-origin',
        headers:{'Content-Type':'application/json', 'X-CSRFToken':root.querySelector('[name="csrfmiddlewaretoken"]').value},
        body:JSON.stringify({id:row.id, revision:row.revision, action}) });
    if (!response.ok) throw new Error('Não foi possível atualizar o vínculo. Recarregue os dados.');
}
async function load() {
    if (busy) return;
    busy = true;
    for (const id of ['ledger-csv', 'ledger-pdf']) document.getElementById(id).classList.add('hide');
    message.textContent = 'Carregando fatura…';
    const chosen = select.value || new URLSearchParams(window.location.search).get('fatura') || '';
    try {
        const response = await fetch(`${root.dataset.url}?bill=${encodeURIComponent(chosen)}`, { credentials:'same-origin' });
        if (!response.ok) throw new Error('Não foi possível carregar a fatura. Confira sua sessão.');
        const data = await response.json();
        select.replaceChildren();
        for (const bill of data.bills) {
            const month = bill.due_date ? new Date(`${bill.due_date}T12:00:00`).toLocaleDateString('pt-BR',{month:'long',year:'numeric'}) : 'Sem vencimento';
            const option = node('option', `${month} · ${bill.account} · ${date(bill.due_date)}`, select);
            option.value = bill.id;
        }
        for (const [value, label] of [['unbilled','Sem fatura definida'],['all','Todas as faturas']]) node('option', label, select).value = value;
        select.value = data.selected_bill;
        document.getElementById('ledger-import').href = `${root.dataset.importUrl}?fonte=pluggy&fatura=${encodeURIComponent(data.selected_bill)}`;
        const csvLink = document.getElementById('ledger-csv');
        csvLink.href = `${csvLink.dataset.exportUrl}?bill=${encodeURIComponent(data.selected_bill)}`;
        csvLink.classList.remove('hide');
        pdfButton.classList.remove('hide');
        const totals = document.getElementById('ledger-totals');
        totals.replaceChildren();
        const bill = data.bills.find((entry) => entry.id === data.selected_bill);
        if (bill) node('h4', `Vencimento ${date(bill.due_date)} · Fechamento ${date(bill.closing_date)} · Total informado pelo banco: ${amount(bill.total,bill.currency)}`, totals);
        for (const [currency, summary] of Object.entries(data.totals)) {
            node('p', `Compras/taxas: ${amount(summary.charges,currency)} · Estornos/outros créditos: ${amount(summary.refunds,currency)} · Total sem pagamentos de fatura: ${amount(summary.net,currency)}`, totals);
            node('p', `Pagamentos de fatura registrados no ciclo: ${amount(summary.payments,currency)} (exibidos separadamente).`, totals);
        }
        node('p', 'Esta visão contém somente dados recebidos do banco, sem projeções locais. Novas faturas aparecem quando disponibilizadas pela fonte.', totals);
        const groups = document.getElementById('ledger-groups');
        groups.replaceChildren();
        const pdfChoices = [];
        function updatePDF() {
            const selected = pdfChoices.filter(choice => choice.checked);
            pdfButton.disabled = !selected.length;
            pdfButton.dataset.downloadUrl = `${pdfButton.dataset.exportUrl}?bill=${encodeURIComponent(data.selected_bill)}`
                + selected.map(choice => `&card=${encodeURIComponent(choice.value)}`).join('');
        }
        for (const group of data.groups) {
            const cardLabel = `${group.card_name ? `${group.card_name} · ` : ''}Final ${group.last_four || 'não informado'}`;
            const section = node('section', null, groups);
            const heading = node('h4', null, section);
            const label = node('label', null, heading);
            const choice = node('input', null, label);
            choice.type = 'checkbox';
            choice.value = `${group.account_id}:${group.last_four}`;
            choice.checked = cardChoices.get(choice.value) ?? true;
            choice.setAttribute('aria-label', `Exportar PDF: ${group.account} · ${cardLabel}`);
            choice.addEventListener('change', () => {
                cardChoices.set(choice.value, choice.checked);
                updatePDF();
            });
            pdfChoices.push(choice);
            node('span', ` ${group.account} · ${cardLabel} · Gastos: ${amount(group.net,group.currency)}`, label);
            node('p', `Compras/taxas ${amount(group.charges,group.currency)} · Créditos ${amount(group.refunds,group.currency)} · Pagamentos de fatura ${amount(group.payments,group.currency)}`, section);
            const scroll = node('div', null, section);
            scroll.className = 'pluggy-table-scroll';
            const table = node('table', null, scroll);
            table.className = 'table pluggy-ledger-table';
            const header = node('tr', null, node('thead', null, table));
            for (const title of ['Compra', 'Lançamento', 'Vencimento', 'Descrição original', 'Parcela', 'Valor', 'Evento', 'Importação']) node('th',title,header);
            const body = node('tbody',null,table);
            for (const row of group.rows) {
                const facts = row.facts;
                const tr = node('tr',null,body);
                for (const value of [date(facts.purchase_date || facts.date),date(facts.date),date(row.due_date),facts.description,
                    facts.payment_type === 'INSTALLMENT' ? `${facts.number}/${facts.total}` : 'À vista',
                    amount(facts.amount,facts.currency),
                    ({purchase:'Compra/taxa',card_payment:'Pagamento da fatura',refund:'Estorno/crédito',unknown:'Revisar'})[row.event]]) node('td',value,tr);
                const cell = node('td', labels[row.state] || row.state, tr);
                if (row.transaction_id) {
                    const link = node('a', ` · Lançamento #${row.transaction_id}`, cell);
                    link.href = `/relatorio_financeiro/${row.transaction_id}/`;
                    for (const [action,title] of [['keep','Manter lançamento revisado'],['unlink','Desfazer vínculo']]) {
                        if (action === 'keep' && row.state !== 'conflict') continue;
                        const button = node('button',title,cell);
                        button.type = 'button';
                        button.className = 'btn btn-default';
                        button.addEventListener('click',async () => {
                            if (busy) return;
                            busy = true;
                            try { await review(row,action); }
                            catch (error) { message.textContent=error.message; return; }
                            finally { busy=false; }
                            await load();
                        });
                    }
                }
            }
        }
        updatePDF();
        message.textContent = `${data.count} lançamento(s) da fonte. Importados e pendentes estão incluídos.`;
    } catch(error) {
        message.textContent=error.message;
    } finally { busy=false; }
}
select.addEventListener('change',load);
load();
