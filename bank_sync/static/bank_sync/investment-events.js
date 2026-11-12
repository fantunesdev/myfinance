const list = document.getElementById('investment-events');
const status = document.getElementById('history-status');
const state = document.getElementById('event-state');
const token = document.querySelector('[name=csrfmiddlewaretoken]').value;
let page = 1;
const states = {new:'Pendente',historical:'Histórico anterior à data-base',conflict:'Alteração na fonte',linked:'Vinculado ao histórico',applied:'Aplicado',ignored:'Ignorado',queued:'Na fila',running:'Em andamento',succeeded:'Concluído',failed:'Falhou'};
const kinds = {BUY:'Compra',SELL:'Venda ou resgate',INTEREST:'Provento',TAX:'Tributo',TRANSFER:'Transferência',AMORTIZATION:'Amortização'};
const el = (tag, text) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; return n; };
async function post(url, data) {
    const r = await fetch(url, {method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRFToken':token},body:JSON.stringify(data)});
    if (!(r.headers.get('content-type') || '').includes('application/json')) throw Error('Entre novamente para continuar.');
    const result = await r.json(); if (!r.ok) throw Error(result.detail || 'Operação indisponível.'); return result;
}
async function load() {
    try {
        const r = await fetch(`${list.dataset.url}?page=${page}&state=${encodeURIComponent(state.value)}`, {credentials:'same-origin'});
        if (!r.ok) throw Error('Não foi possível consultar os eventos.');
        const data = await r.json(); list.replaceChildren();
        for (const event of data.events) {
            const box = el('section'); box.className='box';
            box.append(el('h4',event.titles.join(', ')),el('p',`${event.facts.date || ''} · ${kinds[event.facts.type] || 'Classificação pendente'} · ${event.facts.netAmount ?? event.facts.amount ?? 'Valor não informado'} · ${states[event.state] || event.state}`),el('p',event.reason));
            const select=el('input');select.type='checkbox';select.className='group-event';select.dataset.id=event.id;select.dataset.revision=event.revision;
            const groupLabel=el('label','Agrupar compras ou pernas da transferência ');groupLabel.append(select);box.append(groupLabel);
            const form=el('form');
            const action=el('select');for(const [v,label] of [['link','Vincular ao histórico'],['apply','Aplicar operação'],['ignore','Ignorar com motivo'],['keep','Manter conciliação local após conflito']]) {const o=el('option',label);o.value=v;action.append(o);}
            const existing=el('select');existing.multiple=true;
            for(const m of event.candidates || []) {const o=el('option',`${m.date} · ${m.description} · ${m.type} · R$ ${m.amount}`);o.value=m.id;existing.append(o);}
            const cash=el('select');cash.multiple=true;
            for(const c of event.cash_candidates || []) {const o=el('option',`${c.facts.date} · ${c.facts.description} · ${c.facts.amount}`);o.value=c.id;cash.append(o);}
            const kind=el('select');for(const [v,label] of [['','Manter classificação da fonte'],['income','Confirmar provento recebido'],['sell','Confirmar venda com quantidade comprovada']]){const o=el('option',label);o.value=v;kind.append(o);}
            const evidence=el('textarea');evidence.required=true;evidence.placeholder='Explique a correspondência e a evidência de liquidação.';
            const principal=el('input');principal.type='number';principal.step='0.01';principal.placeholder='Custo da parcela vendida (se comprovado)';
            const sharedCost=el('input');sharedCost.type='number';sharedCost.min='0';sharedCost.step='0.01';sharedCost.placeholder='Custo compartilhado comprovado na nota';
            const credits=el('div');
            for(const c of data.credits || []) {const line=el('label',`${c.date} · ${c.notes || 'Crédito de caixa'} · disponível R$ ${c.available} `);const amount=el('input');amount.type='number';amount.min='0';amount.max=c.available;amount.step='0.01';amount.dataset.credit=c.id;line.append(amount);credits.append(line);}
            form.append(action,kind,el('p','Lançamentos existentes:'),existing,el('p','Liquidações bancárias:'),cash,principal,el('p','Para compras: distribua o débito entre os créditos de origem.'),credits,sharedCost,evidence,el('button','Confirmar conciliação'));
            form.addEventListener('submit',async e=>{e.preventDefault();const button=form.querySelector('button');button.disabled=true;try {
                await post(`${window.location.pathname}${event.id}/`,{events:[...list.querySelectorAll('.group-event:checked')].map(i=>({id:Number(i.dataset.id),revision:Number(i.dataset.revision)})),shared_cost:sharedCost.value||'0',kind:kind.value||null,revision:event.revision,action:action.value,evidence:evidence.value,principal:principal.value || null,movement_ids:[...existing.selectedOptions].map(o=>Number(o.value)),cash_ids:[...cash.selectedOptions].map(o=>Number(o.value)),allocations:[...credits.querySelectorAll('input')].filter(i=>Number(i.value)>0).map(i=>({credit_id:Number(i.dataset.credit),amount:i.value}))});
                status.textContent='Conciliação registrada.';await load();
            } catch(err){status.textContent=err.message;}finally {button.disabled=false;}});
            box.append(form);list.append(box);
        }
        const running=data.jobs.find(j=>['queued','running'].includes(j.state));
        if(running){status.textContent=`${states[running.state]}: ${running.progress.titles || 0} de ${running.progress.total_titles || '?'} investimentos consultados.`;setTimeout(load,3000);}
        else if(data.jobs[0]) status.textContent=data.jobs[0].message || states[data.jobs[0].state];
        document.getElementById('next-page').disabled=page*30>=data.count;
        document.getElementById('previous-page').disabled=page<=1;
    } catch(e){status.textContent=e.message;}
}
document.getElementById('history-job').addEventListener('submit',async e=>{e.preventDefault();try {await post(e.target.action,{});await load();}catch(err){status.textContent=err.message;}});
state.addEventListener('change',()=>{page=1;load();});
document.getElementById('next-page').addEventListener('click',()=>{page++;load();});
document.getElementById('previous-page').addEventListener('click',()=>{page--;load();});
load();
