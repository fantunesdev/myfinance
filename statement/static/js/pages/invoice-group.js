// Versão mínima e validada de invoice-group.js
// Adiciona uma interface de agrupamento em tempo de execução (selecionar grupos, agrupar, desagrupar).

function parseCurrencyToFloat(text) {
    if (!text) return 0;
    const cleaned = String(text).replace(/[R$\s]/g, '').replace(/\./g, '').replace(',', '.');
    const n = parseFloat(cleaned);
    return Number.isFinite(n) ? n : 0;
}

function buildPanel(groups, anchorRect) {
    const panel = document.createElement('div');
    // Usar tema do projeto (escuro) e fundo escuro explícito para evitar transparência
    panel.className = 'invoice-group-panel card bg-dark text-light';
    panel.style.position = 'absolute';
    panel.style.zIndex = 9999;
    panel.style.padding = '8px';
    panel.style.boxShadow = '0 2px 6px rgba(0,0,0,0.6)';
    panel.style.background = '#0b0b0b';
    panel.style.backgroundColor = '#0b0b0b';
    panel.style.border = '1px solid rgba(255,255,255,0.04)';
    panel.style.minWidth = '220px';
    panel.style.color = '#fff';
    panel.style.textAlign = 'left';

    const list = document.createElement('div');
    list.style.textAlign = 'left';
    list.style.paddingLeft = '6px';
    groups.forEach(g => {
        const row = document.createElement('label');
        row.style.display = 'block';
        row.style.marginBottom = '6px';
        row.style.textAlign = 'left';
        const cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.dataset.cardNumberId = g.cardNumberId || '';
        cb.style.marginRight = '8px';
        row.appendChild(cb);
        row.appendChild(document.createTextNode(g.label));
        list.appendChild(row);
    });

    const actions = document.createElement('div');
    actions.style.marginTop = '8px';
    actions.style.textAlign = 'right';
    const btnCancel = document.createElement('button'); btnCancel.type = 'button'; btnCancel.textContent = 'Cancelar'; btnCancel.className = 'btn btn-outline-light'; btnCancel.style.marginRight = '8px';
    const btnOk = document.createElement('button'); btnOk.type = 'button'; btnOk.textContent = 'Agrupar selecionados'; btnOk.className = 'btn btn-primary';
    btnCancel.addEventListener('click', () => panel.remove());
    actions.appendChild(btnCancel); actions.appendChild(btnOk);

    panel.appendChild(list); panel.appendChild(actions);
    const top = (anchorRect.top + window.scrollY) + anchorRect.height + 6;
    const left = (anchorRect.left + window.scrollX);
    panel.style.top = `${top}px`; panel.style.left = `${left}px`;
    document.body.appendChild(panel);
    return {panel, btnOk};
}

function collectGroups() {
    const groups = [];
    const root = document.getElementById('statement-table') || document;
    root.querySelectorAll('tr.group-header').forEach((h, idx) => {
        const labelEl = h.querySelector('strong');
        const label = labelEl ? labelEl.textContent.trim() : `Group ${idx}`;
        const cardNumberId = h.getAttribute('data-card-number-id');
        groups.push({index: idx, label, cardNumberId, header: h});
    });
    return groups;
}

const invoiceGroupUndoStack = [];

function mergeGroupsCreateNew(selectedIds) {
    if (!selectedIds || selectedIds.length === 0) return;
    const origTable = document.getElementById('statement-table') || document.querySelector('table'); if (!origTable) return;

    // Evitar criar múltiplas tabelas agrupadas se o usuário clicar várias vezes sem desagrupar 
    // (pode ser melhorado para permitir múltiplos agrupamentos, mas por simplicidade vamos bloquear por enquanto)
    if (document.querySelector('table[data-created-grouped="1"]')) return;

    // Tirar um snapshot completo do HTML da tabela original para podermos recriá-la do zero
    const originalSnapshot = origTable.outerHTML;
    // Remover primeiro qualquer linha de total do grupo para os grupos selecionados
    selectedIds.forEach(id => {
        const hdr = origTable.querySelector(`tr.group-header[data-card-number-id="${id}"]`);
        if (!hdr) return;
        let x = hdr.nextElementSibling;
        while (x && !x.classList.contains('group-header')) {
            const next = x.nextElementSibling;
            if (x.classList && x.classList.contains('group-total-row')) {
                x.parentElement.removeChild(x);
                break;
            }
            x = next;
        }
    });

    const groups = selectedIds.map(id => {
        const header = origTable.querySelector(`tr.group-header[data-card-number-id="${id}"]`);
        if (!header) return null;
        const nodes = [];
        // Incluir o cabeçalho
        nodes.push(header);
        let el = header.nextElementSibling;
        while (el && !el.classList.contains('group-header')) {
            nodes.push(el);
            if (el.classList && el.classList.contains('group-total-row')) break;
            el = el.nextElementSibling;
        }
        return {id, nodes};
    }).filter(Boolean);

    if (groups.length === 0) return;

    // Recriar a tabela a partir do snapshot e manipular a nova tabela de forma limpa
    const wrapper = document.createElement('div');
    wrapper.innerHTML = originalSnapshot;
    const newTable = wrapper.firstElementChild;
    if (!newTable) return;

    const tbody = newTable.tBodies[0] || newTable.querySelector('tbody') || newTable;
    const createdRows = [];
    const removedGroupsLocal = [];

    // Cara cada id de grupo selecionado, encontrar seu cabeçalho na nova tabela e coletar/remover nós
    groups.forEach(g => {
        const header = newTable.querySelector(`tr.group-header[data-card-number-id="${g.id}"]`);
        if (!header) return;
        const nodes = [];
        nodes.push(header);
        let el = header.nextElementSibling;
        while (el && !el.classList.contains('group-header')) {
            nodes.push(el);
            if (el.classList && el.classList.contains('group-total-row')) break;
            el = el.nextElementSibling;
        }

        const nodeHtmls = nodes.map(n => n.outerHTML);
        const last = nodes[nodes.length - 1];
        const after = last ? last.nextElementSibling : null;

        nodes.forEach(n => {
            const isMeta = n.classList && (n.classList.contains('group-header') || n.classList.contains('group-total-row') || n.classList.contains('group-empty'));
            if (!isMeta) createdRows.push(n.cloneNode(true));
            // Remover da nova tabela
            if (n && n.parentElement) n.parentElement.removeChild(n);
        });

        removedGroupsLocal.push({after: after, nodesHtml: nodeHtmls});
    });

    // Calcular o total a partir das linhas criadas
    let total = 0;
    let amountIndex = null;
    const headerRow = origTable.querySelector('thead tr') || origTable.querySelector('tbody tr');
    if (headerRow) {
        const headers = Array.from(headerRow.querySelectorAll('th,td'));
        for (let i = 0; i < headers.length; i++) {
            const h = headers[i];
            const txt = (h.textContent || '').toLowerCase();
            if (h.classList.contains('amount') || h.classList.contains('valor') || /valor|amount|valor a pagar/.test(txt)) { amountIndex = i; break; }
        }
        if (amountIndex === null) amountIndex = Math.max(0, headers.length - 1);
    }
    Array.from(createdRows).forEach(r => {
        const cells = Array.from(r.querySelectorAll('td,th'));
        let cell = null;
        if (amountIndex !== null && cells.length > amountIndex) cell = cells[amountIndex];
        if (!cell) cell = r.querySelector('td.amount, td.valor, td.value') || r.querySelector('td:last-child');
        if (cell) total += parseCurrencyToFloat(cell.textContent);
    });

    const totalTr = document.createElement('tr');
    totalTr.className = 'group-total-row';
    const td = document.createElement('td');
    let colCount = 0;
    const hdrRow = origTable.querySelector('thead tr');
    if (hdrRow) colCount = hdrRow.querySelectorAll('th,td').length;
    if (!colCount) {
        const firstRow = origTable.querySelector('tbody tr');
        if (firstRow) colCount = firstRow.querySelectorAll('td').length;
    }
    td.colSpan = colCount || 1;
    td.textContent = 'Total: R$ ' + total.toFixed(2).replace('.', ',');
    totalTr.appendChild(td);

    // Determinar o ponto de inserção no tbody da nova tabela
    let insertionPoint = null;
    for (let i = 0; i < removedGroupsLocal.length; i++) {
        const rg = removedGroupsLocal[i];
        if (rg.after && rg.after.parentElement === tbody) { insertionPoint = rg.after; break; }
    }

    const createdId = 'grouped-' + Date.now();

    // Criar cabeçalho rotulado incluindo nomes dos cardnumbers selecionados
    const selectedNames = selectedIds.map(id => {
        const h = origTable.querySelector(`tr.group-header[data-card-number-id="${id}"]`);
        const s = h && h.querySelector('strong');
        return s ? s.textContent.trim() : null;
    }).filter(Boolean);
    const headerTr = document.createElement('tr'); headerTr.className = 'group-header grouped-created'; headerTr.setAttribute('data-created-id', createdId);
    const th = document.createElement('td'); th.colSpan = colCount || 1; th.innerHTML = '<strong>Agrupados' + (selectedNames.length ? ' (' + selectedNames.join(' + ') + ')' : '') + '</strong>'; headerTr.appendChild(th);

    if (insertionPoint && insertionPoint.parentElement === tbody) {
        tbody.insertBefore(headerTr, insertionPoint);
        createdRows.forEach(r => { r.setAttribute('data-created-id', createdId); tbody.insertBefore(r, insertionPoint); });
        tbody.insertBefore(totalTr, insertionPoint);
    } else {
        tbody.appendChild(headerTr);
        createdRows.forEach(r => { r.setAttribute('data-created-id', createdId); tbody.appendChild(r); });
        tbody.appendChild(totalTr);
    }

    // Substituir a tabela original pela nova tabela (destruir a original)
    origTable.parentElement.replaceChild(newTable, origTable);

    invoiceGroupUndoStack.push({createdId: createdId, removedGroups: removedGroupsLocal, originalSnapshot: originalSnapshot});
}

function undoLastGrouping() {
    const action = invoiceGroupUndoStack.pop(); if (!action) return;
    const createdId = action.createdId || action.createdTableId;
    if (action.originalSnapshot) {
        // Restaurar snapshot substituindo a tabela atual pelo HTML original
        const wrapper = document.createElement('div');
        wrapper.innerHTML = action.originalSnapshot;
        const orig = wrapper.firstElementChild;
        const currentTable = document.getElementById('statement-table') || document.querySelector('table');
        if (orig && currentTable && currentTable.parentElement) {
            currentTable.parentElement.replaceChild(orig, currentTable);
        }
        return;
    }
    if (createdId) {
        // Alternativa: remover quaisquer linhas/cabeçalho/total criados e inseridos com este id
        const createdElems = Array.from(document.querySelectorAll(`[data-created-id="${createdId}"]`));
        createdElems.forEach(el => { if (el && el.parentElement) el.parentElement.removeChild(el); });
    }

    // Restaurar o conteúdo dos grupos removidos
    if (action.removedGroups && action.removedGroups.length) {
        action.removedGroups.forEach(rg => {
            const parent = rg.parent;
            const after = rg.after; // may be null
            const html = rg.nodesHtml.join('');
            const wrapper = document.createElement('table');
            wrapper.innerHTML = '<tbody>' + html + '</tbody>';
            const src = wrapper.tBodies[0];
            while (src && src.firstChild) {
                if (after && after.parentElement === parent) {
                    parent.insertBefore(src.firstChild, after);
                } else {
                    parent.appendChild(src.firstChild);
                }
            }
        });
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const table = document.querySelector('table'); if (!table) return;
    const wrapper = document.createElement('div'); wrapper.className = 'invoice-group-actions mb-2'; wrapper.style.display = 'flex'; wrapper.style.gap = '8px';
    const globalBtn = document.createElement('button'); globalBtn.type = 'button'; globalBtn.className = 'btn btn-sm btn-secondary'; globalBtn.textContent = 'Agrupar'; wrapper.appendChild(globalBtn);
    const undoBtn = document.createElement('button'); undoBtn.type = 'button'; undoBtn.className = 'btn btn-sm btn-light'; undoBtn.textContent = 'Desagrupar'; undoBtn.disabled = true; wrapper.appendChild(undoBtn);
    table.parentElement.insertBefore(wrapper, table);
    globalBtn.addEventListener('click', () => {
        const groups = collectGroups().filter(g => g.cardNumberId);
        const {panel, btnOk} = buildPanel(groups, globalBtn.getBoundingClientRect());
        btnOk.addEventListener('click', () => { const checks = panel.querySelectorAll('input[type="checkbox"]:checked'); const ids = Array.from(checks).map(c => c.dataset.cardNumberId).filter(Boolean); mergeGroupsCreateNew(ids); panel.remove(); undoBtn.disabled = invoiceGroupUndoStack.length === 0; });
    });
    undoBtn.addEventListener('click', () => { undoLastGrouping(); undoBtn.disabled = invoiceGroupUndoStack.length === 0; });
});
