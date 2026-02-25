
document.addEventListener('DOMContentLoaded', function(){
    const table = document.getElementById('statement-table');
    const toggleBtn = document.getElementById('toggle-checkboxes');
    if(!table || !toggleBtn) return;

    // Garantir estado inicial: escondido
    try{
        table.classList.remove('show-checkboxes');
        table.dataset.checkboxVisible = 'false';
    }catch(e){}

    // Carregar linhas ocultas persistidas para esta página
    try{
        const hadHidden = loadHiddenRows(table);
        if(hadHidden){
            setToggleIcon(toggleBtn, true);
            refreshZebra(table);
            recalcDashboardTotals(table);
        }
    }catch(e){ console.error('loadHiddenRows error', e); }
    // Carregar grupos e marcar linhas agrupadas (se houver)
    try{ loadGroups(table); }catch(e){ console.error('loadGroups error', e); }
    try{ updateMainToggleIcon(table, toggleBtn); }catch(e){}

    // Adicionar checkbox 'selecionar todos' no cabeçalho (se a tabela tiver coluna de checkbox)
    try{
        const thead = table.tHead;
        if(thead && thead.rows && thead.rows.length){
            const headerRow = thead.rows[0];
            // Tentar encontrar um th com a classe 'checkbox-col' ou usar o primeiro th
            let th = headerRow.querySelector('th.checkbox-col');
            if(!th) th = headerRow.querySelector('th');
            if(th){
                // Criar checkbox "selecionar todos"
                const selectAll = document.createElement('input');
                selectAll.type = 'checkbox';
                selectAll.className = 'myfinance-select-all';
                selectAll.title = 'Selecionar todos';
                // Inserir checkbox no início do th
                th.insertBefore(selectAll, th.firstChild);

                // Quando selectAll mudar, marcar/desmarcar todos os checkboxes das linhas
                selectAll.addEventListener('change', function(){
                    const checked = !!this.checked;
                    const tbody = table.tBodies[0];
                    if(!tbody) return;
                    const inputs = tbody.querySelectorAll('input[type="checkbox"]');
                    inputs.forEach(i => { i.checked = checked; });
                });

                // Manter o estado do selectAll sincronizado com mudanças dos checkboxes das linhas (delegação)
                const tbody = table.tBodies[0];
                if(tbody){
                    tbody.addEventListener('change', function(e){
                        if(!e.target || e.target.type !== 'checkbox') return;
                        updateSelectAllState(table);
                    });
                }
            }
        }
    }catch(e){ console.error('select-all init error', e); }

    toggleBtn.addEventListener('click', function(event){
        // Sempre abrir o popup e NÃO revelar automaticamente nem limpar linhas ocultas.
        const currently = table.dataset.checkboxVisible === 'true';
        const next = !currently;
        if(next){
            table.classList.add('show-checkboxes');
            table.dataset.checkboxVisible = 'true';
            toggleBtn.setAttribute('title','Ocultar checkboxes');
        } else {
            table.classList.remove('show-checkboxes');
            table.dataset.checkboxVisible = 'false';
            toggleBtn.setAttribute('title','Mostrar checkboxes');
        }
        // Mostrar popup de opções (não alterar linhas ocultas)
        showOptionsPopup(event.currentTarget, table, toggleBtn);
    });

    // Observar mudanças de classe na tabela para fechar o popup quando a coluna de checkboxes for escondida
    const mo = new MutationObserver(function(mutations){
        for(const m of mutations){
            if(m.attributeName === 'class'){
                if(!table.classList.contains('show-checkboxes')){
                    // Fechar popup se a coluna de checkboxes for escondida
                    closeCheckboxPopup();
                }
            }
        }
    });
    mo.observe(table, { attributes: true, attributeFilter: ['class'] });
});

function showOptionsPopup(anchorEl, table, toggleBtn){
    // Remover popup existente se houver (pode acontecer se o usuário clicar rapidamente várias vezes no ícone)
    const existing = document.querySelector('.myfinance-checkbox-popup');
    if(existing) existing.remove();

    const popup = document.createElement('div');
    popup.className = 'myfinance-checkbox-popup';
    popup.setAttribute('role','dialog');

    const select = document.createElement('select');
    select.className = 'myfinance-checkbox-select';
    const opt1 = document.createElement('option'); opt1.value='hide'; opt1.text = 'Ocultar';
    const opt2 = document.createElement('option'); opt2.value='group'; opt2.text = 'Agrupar';
    const opt3 = document.createElement('option'); opt3.value='hide-groups'; opt3.text = 'Ocultar grupos';
    select.appendChild(opt1); select.appendChild(opt2); select.appendChild(opt3);

    // Container de ações (select + botão Aplicar)
    const actions = document.createElement('div');
    actions.className = 'myfinance-checkbox-actions';
    actions.appendChild(select);

    // Input de texto para nome do grupo (oculto por padrão)
    const groupNameInput = document.createElement('input');
    groupNameInput.type = 'text';
    groupNameInput.placeholder = 'Nome do grupo';
    groupNameInput.className = 'myfinance-group-name';
    groupNameInput.style.display = 'none';
    actions.appendChild(groupNameInput);

    const applyBtn = document.createElement('button');
    applyBtn.type = 'button';
    applyBtn.className = 'btn btn-danger myfinance-checkbox-apply';
    applyBtn.textContent = 'Aplicar';
    actions.appendChild(applyBtn);

    popup.appendChild(actions);
    document.body.appendChild(popup);

    // posicionar próximo ao ícone: usar posição fixa (viewport) para que o popup
    // permaneça alinhado ao ícone mesmo quando o documento for rolado.
    popup.style.position = 'fixed';

    function reposition(){
        const r = anchorEl.getBoundingClientRect();
        const pw = popup.offsetWidth || 0;
        const ph = popup.offsetHeight || 0;
        // preferir à esquerda do ícone
        let left = r.left - pw - 8;
        const minLeft = 6;
        const maxLeft = window.innerWidth - pw - 6;
        if(left < minLeft) left = r.right + 8; // try place to right
        if(left < minLeft) left = minLeft;
        if(left > maxLeft) left = maxLeft;

        let top = r.top + (r.height - ph) / 2;
        const minTop = 6;
        const maxTop = window.innerHeight - ph - 6;
        if(top < minTop) top = minTop;
        if(top > maxTop) top = maxTop;

        popup.style.left = left + 'px';
        popup.style.top = top + 'px';
    }

    // posicionamento inicial após o layout
    requestAnimationFrame(reposition);
    // container de grupos (renderizado sob demanda quando 'Ocultar grupos' for selecionado)
    const groupsContainer = document.createElement('div');
    groupsContainer.className = 'myfinance-groups-list';
    groupsContainer.style.display = 'none';
    popup.appendChild(groupsContainer);
    // reposicionar em scroll/resize para manter próximo ao ícone
    const onScroll = () => requestAnimationFrame(reposition);
    window.addEventListener('scroll', onScroll, { passive: true });
    popup._onScroll = onScroll;

    // foco para teclado
    select.focus();

    function cleanup(){
        popup.remove();
        try{ if(popup._onResize) window.removeEventListener('resize', popup._onResize); }catch(e){}
    }

    // OBS: NÃO fechar o popup ao clicar fora; somente o ícone do olho ou chamadas
    // programáticas devem fechá-lo. Ainda registramos resize/scroll para reposicionar
    // ou remover o popup conforme mudanças na viewport.
    window.addEventListener('resize', cleanup);
    popup._onResize = cleanup;

    // Mostrar/ocultar input de nome do grupo ou lista de grupos dependendo da seleção
    select.addEventListener('change', function(){
        if(select.value === 'group'){
            groupNameInput.style.display = 'inline-block';
            groupNameInput.focus();
            // Ocultar lista de grupos e descrições ocultas se estavam visíveis de uma seleção anterior
            if(groupsContainer) groupsContainer.style.display = 'none';
            hiddenDesc.style.display = 'none';
        } else if(select.value === 'hide-groups'){
            groupNameInput.style.display = 'none';
            const gc = popup.querySelector('.myfinance-groups-list');
            if(gc){ gc.style.display = 'block'; renderGroupsList(gc, table); }
            hiddenDesc.style.display = 'none';
        } else {
            groupNameInput.style.display = 'none';
            if(groupsContainer) groupsContainer.style.display = 'none';
            // Quando 'Ocultar' estiver selecionado, mostrar descrições das transações atualmente ocultas
            if(select.value === 'hide'){
                hiddenDesc.style.display = 'block';
                renderHiddenDescriptions();
            } else {
                hiddenDesc.style.display = 'none';
            }
        }
    });

    // Bloco de descrições ocultas (mostra descrições das transações atualmente ocultas quando 'Ocultar' está selecionado)
    const hiddenDesc = document.createElement('div');
    hiddenDesc.className = 'myfinance-hidden-descriptions';
    hiddenDesc.style.display = 'none';
    popup.appendChild(hiddenDesc);

    // Ao abrir o popup, se o select já estiver em 'Ocultar' e houver linhas ocultas
    // nesta página, renderizá-las imediatamente para que o usuário veja a lista
    // sem precisar mudar o select.
    if(select.value === 'hide'){
        hiddenDesc.style.display = 'block';
        renderHiddenDescriptions();
    } else if(select.value === 'hide-groups'){
        // Se o valor padrão for 'hide-groups', mostrar grupos
        groupsContainer.style.display = 'block';
        renderGroupsList(groupsContainer, table);
    }

    function renderHiddenDescriptions(){
        hiddenDesc.innerHTML = '';
            // Listar apenas transações ocultas que não pertencem a grupos
        const rows = Array.from(table.querySelectorAll('tbody tr.row-hidden')).filter(r => !r.classList.contains('row-hidden-by-group'));
        if(!rows.length){
            hiddenDesc.textContent = 'Nenhuma transação oculta.';
            return;
        }
        const list = document.createElement('ul'); list.style.paddingLeft = '16px'; list.style.margin = '6px 0';
        for(const r of rows){
            const id = r.getAttribute('data-tx-id') || '';
            const li = document.createElement('li'); li.style.display = 'flex'; li.style.alignItems = 'center'; li.style.gap = '8px';
            const text = document.createElement('span'); text.textContent = getRowDescription(r) || ('ID ' + id);
            li.appendChild(text);
            // Ícone de revelar (olho) para mostrar esta transação
            const ic = document.createElement('i'); ic.className = 'fa-solid fa-eye'; ic.title = 'Revelar transação'; ic.style.cursor = 'pointer'; ic.style.marginLeft = 'auto';
            ic.addEventListener('click', function(){
                // Revelar esta linha (remover flags de oculto manual)
                try{
                    if(r.classList.contains('row-hidden')) r.classList.remove('row-hidden');
                    if(r.classList.contains('row-hidden-by-manual')) r.classList.remove('row-hidden-by-manual');
                    refreshZebra(table);
                    recalcDashboardTotals(table);
                    saveHiddenRows(table);
                    showToast('Transação revelada', 'success');
                    const toggleBtn = document.getElementById('toggle-checkboxes'); if(toggleBtn) updateMainToggleIcon(table, toggleBtn);
                    renderHiddenDescriptions();
                }catch(e){ console.error('reveal single row error', e); }
            });
            li.appendChild(ic);
            list.appendChild(li);
        }
        hiddenDesc.appendChild(list);
    }

    function getRowDescription(row){
            try{
                // Priorizar atributos data explícitos primeiro
                const selAttrs = row.querySelector('[data-description], [data-desc], [data-descicao], td.description, td.desc, .description, .tx-desc');
                if(selAttrs && selAttrs.textContent) return selAttrs.textContent.trim();

                // Testar classes que podem conter variantes em Português/Inglês
                const classCandidates = ['.descricao', '.descricao-cell', '.description', '.desc', '.tx-desc', '.description-cell'];
                for(const s of classCandidates){
                    const el = row.querySelector(s);
                    if(el && el.textContent) return el.textContent.trim();
                }

                // Fallback: tentar encontrar a coluna do cabeçalho que contenha "descr" (descrição/description)
                const table = row.closest('table');
                if(table && table.tHead && table.tHead.rows.length){
                    const headers = Array.from(table.tHead.rows[0].querySelectorAll('th'));
                    for(let i=0;i<headers.length;i++){
                        const h = headers[i];
                        const ht = (h.textContent || '').toLowerCase();
                        if(ht.includes('descr')){
                            const tds = row.querySelectorAll('td');
                            if(tds && tds[i] && tds[i].textContent) return tds[i].textContent.trim();
                        }
                    }
                }

                // Último recurso: primeira célula que não seja checkbox (evitar retornar data quando possível)
                const tds = Array.from(row.querySelectorAll('td'));
                for(const td of tds){
                    if(td.classList && td.classList.contains('checkbox-cell')) continue;
                    const txt = td.textContent.trim();
                    if(txt) return txt;
                }
                return '';
            }catch(e){ return ''; }
    }

    // Aplicar ação quando clicar no botão Aplicar
    applyBtn.addEventListener('click', function(){
        const v = select.value;
        if(v === 'hide'){
            hideCheckedRows(table);
            // Alterar ícone para eye-slash quando linhas foram ocultadas
            setToggleIcon(toggleBtn, true);
            // Sucesso, fechar popup e limpar checkboxes
            try{ table.classList.remove('show-checkboxes'); table.dataset.checkboxVisible = 'false'; toggleBtn.setAttribute('title','Mostrar checkboxes'); }catch(e){}
            cleanup();
            return;
        } else if(v === 'group'){
            const name = (groupNameInput.value || '').trim();
            if(!name){
                // Nada a fazer se o nome do grupo estiver vazio
                try{ table.classList.remove('show-checkboxes'); table.dataset.checkboxVisible = 'false'; toggleBtn.setAttribute('title','Mostrar checkboxes'); }catch(e){}
                cleanup();
                return;
            }
            const saved = saveGroup(table, name);
            if(!saved){
                // Usuário cancelou a sobrescrição ou nada foi salvo — não ocultar/fechar
                return;
            }
            // Salvo com sucesso -> notificar usuário, limpar checkboxes mas MANTER o popup aberto
            try{ clearAllCheckboxes(table); }catch(e){}
            try{ updateMainToggleIcon(table, toggleBtn); }catch(e){}
            showToast('Grupo salvo', 'success');
            // Re-renderizar a lista de grupos no popup se estiver visível
            const popupNow = document.querySelector('.myfinance-checkbox-popup');
            if(popupNow){ const gc = popupNow.querySelector('.myfinance-groups-list'); if(gc && gc.style.display !== 'none') renderGroupsList(gc, table); }
            // Manter popup aberto para que o usuário possa imediatamente escolher ocultar
            // Limpar o input do nome do grupo para conveniência
            try{ groupNameInput.value = ''; }catch(e){}
            return;
        } else if(v === 'hide-groups'){
            hideGroups(table);
            setToggleIcon(toggleBtn, true);
            try{ table.classList.remove('show-checkboxes'); table.dataset.checkboxVisible = 'false'; toggleBtn.setAttribute('title','Mostrar checkboxes'); }catch(e){}
            cleanup();
            return;
        }
    });

    // Também permitir que Enter no select dispare o Aplicar
    select.addEventListener('keydown', function(e){
        if(e.key === 'Enter'){
            e.preventDefault();
            applyBtn.click();
        }
    });
}

/* Auxiliar de toast */
function showToast(message, type){
    try{
        const t = document.createElement('div');
        t.className = 'myfinance-toast ' + (type || 'info');
        t.textContent = message;
        document.body.appendChild(t);
        // Disparar exibição
        requestAnimationFrame(()=> t.classList.add('visible'));
        setTimeout(()=>{ t.classList.remove('visible'); setTimeout(()=> t.remove(), 300); }, 3000);
    }catch(e){ console.error('showToast error', e); }
}

function updateSelectAllState(table){
    try{
        const thead = table.tHead;
        if(!thead) return;
        const headerCheckbox = thead.querySelector('input.myfinance-select-all');
        if(!headerCheckbox) return;
        const tbody = table.tBodies[0]; if(!tbody) return;
        const inputs = Array.from(tbody.querySelectorAll('input[type="checkbox"]'));
        if(!inputs.length){ headerCheckbox.checked = false; headerCheckbox.indeterminate = false; return; }
        const checkedCount = inputs.filter(i => i.checked).length;
        if(checkedCount === 0){ headerCheckbox.checked = false; headerCheckbox.indeterminate = false; }
        else if(checkedCount === inputs.length){ headerCheckbox.checked = true; headerCheckbox.indeterminate = false; }
        else { headerCheckbox.checked = false; headerCheckbox.indeterminate = true; }
    }catch(e){ console.error('updateSelectAllState error', e); }
}

function clearAllCheckboxes(table){
    try{
        const tbody = table.tBodies[0]; if(!tbody) return;
        const inputs = tbody.querySelectorAll('input[type="checkbox"]');
        inputs.forEach(i => { i.checked = false; });
        updateSelectAllState(table);
    }catch(e){ console.error('clearAllCheckboxes error', e); }
}

// Remover popup programaticamente (usado quando a coluna de checkbox é escondida)
function closeCheckboxPopup(){
    const popup = document.querySelector('.myfinance-checkbox-popup');
    if(!popup) return;
    try{ if(popup._onScroll) window.removeEventListener('scroll', popup._onScroll); }catch(e){}
    try{ if(popup._onResize) window.removeEventListener('resize', popup._onResize); }catch(e){}
    popup.remove();
}

function hideCheckedRows(table){
    try{
        const tbody = table.tBodies[0];
        if(!tbody) return;
        const rows = Array.from(tbody.rows);
        const applied = [];
        for(const row of rows){
            // Encontrar o checkbox dentro da linha (input da célula de checkbox)
            const cb = row.querySelector('td.checkbox-cell input[type="checkbox"], input[type="checkbox"]');
            if(cb && cb.checked){
                row.classList.add('row-hidden');
                row.classList.add('row-hidden-by-manual');
                const id = row.getAttribute('data-tx-id') || null;
                if(id) applied.push(id);
            }
        }
        try{ console.debug && console.debug('hideCheckedRows applied ids', applied); }catch(e){}
        // Recalcular zebra após ocultar
        refreshZebra(table);
        recalcDashboardTotals(table);
        saveHiddenRows(table);
        showToast('Linhas ocultadas manualmente', 'success');
        const toggleBtn = document.getElementById('toggle-checkboxes'); if(toggleBtn) updateMainToggleIcon(table, toggleBtn);
        // Atualizar descrições ocultas no popup se ele estiver aberto e mostrando 'Ocultar'
        const popup = document.querySelector('.myfinance-checkbox-popup');
        if(popup){ const hd = popup.querySelector('.myfinance-hidden-descriptions'); if(hd && hd.style.display !== 'none') renderHiddenDescriptions(); }
    }catch(e){ console.error('hideCheckedRows error', e); }
}

function revealHiddenRows(table){
    try{
        const tbody = table.tBodies[0];
        if(!tbody) return;
        const rows = Array.from(tbody.querySelectorAll('tr.row-hidden-by-manual'));
        for(const row of rows){
            row.classList.remove('row-hidden');
            row.classList.remove('row-hidden-by-manual');
        }
        refreshZebra(table);
        recalcDashboardTotals(table);
        clearHiddenRows(table);
        showToast('Linhas ocultas manualmente reveladas', 'success');
        const toggleBtn = document.getElementById('toggle-checkboxes'); if(toggleBtn) updateMainToggleIcon(table, toggleBtn);
        const popup = document.querySelector('.myfinance-checkbox-popup');
        if(popup){ const hd = popup.querySelector('.myfinance-hidden-descriptions'); if(hd && hd.style.display !== 'none') renderHiddenDescriptions(); }
    }catch(e){ console.error('revealHiddenRows error', e); }
}

function recalcDashboardTotals(table){
    try{
        const tbody = table.tBodies[0];
        if(!tbody) return;
        const rows = Array.from(tbody.rows).filter(r => !r.classList.contains('row-hidden'));
        let sum = 0;
        for(const r of rows){
            const v = r.getAttribute('data-value');
            if(!v) continue;
            const n = parseFloat(String(v).replace(',','.'));
            if(!isNaN(n)) sum += n;
        }

        // Formatar como BRL
        const fmt = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
        const text = fmt.format(sum);

        // Atualizar total do dashboard, se presente
        const dashTotal = document.querySelector('.dashboard .expenses b.font-16');
        if(dashTotal){
            dashTotal.textContent = 'Total de gastos: ' + text;
        }

        // Atualizar elemento de total móvel
        const mobileTotal = document.querySelector('.mobile-total');
        if(mobileTotal){
            mobileTotal.textContent = 'Total: ' + text;
        }
    }catch(e){ console.error('recalcDashboardTotals error', e); }
}

/* Group helpers */
function groupsStorageKey(table){
    // Preferir uma chave de página estável se a tabela fornecer (data-page-key).
    // caso contrário, usar o pathname.
    try{
        let pageKey = table && table.dataset && table.dataset.pageKey ? table.dataset.pageKey : window.location.pathname;
        // se o pathname contém 'mes_atual', substituir por yyyy/MM/ considerando next_month_view
        try{
            if(String(pageKey).includes('mes_atual')){
                const now = new Date();
                // Ler next_month_view do sessionStorage
                try{
                    const raw = sessionStorage.getItem('next_month_view');
                    if(raw){
                        const cfg = JSON.parse(raw);
                        if(cfg && cfg.active && typeof cfg.day === 'number'){
                            if(now.getDate() > cfg.day){
                                // Avançar um mês
                                now.setMonth(now.getMonth() + 1);
                            }
                        }
                    }
                }catch(e){}
                const yyyy = now.getFullYear();
                const mm = String(now.getMonth() + 1).padStart(2,'0');
                // Usar formato yyyy/MM/ (barra final) para corresponder ao padrão esperado
                pageKey = String(pageKey).replace(/mes_atual/g, `${yyyy}/${mm}/`);
            }
        }catch(e){}
        const key = 'myfinance:groups:' + pageKey;
        try{ console.debug && console.debug('groupsStorageKey ->', key); }catch(e){}
        return key;
    }catch(e){ return 'myfinance:groups:' + window.location.pathname; }
}

function loadGroups(table){
    try{
        const gKey = groupsStorageKey(table);
        try{ console.debug && console.debug('loadGroups key:', gKey); }catch(e){}
        const raw = localStorage.getItem(gKey);
        try{ console.debug && console.debug('loadGroups raw:', raw); }catch(e){}
        if(!raw) return [];
        const groups = JSON.parse(raw || '[]');
        try{ console.debug && console.debug('loadGroups parsed count:', Array.isArray(groups)?groups.length:0); }catch(e){}
        if(!Array.isArray(groups)) return [];

        // Tentar aplicar grupos às linhas; as linhas podem ser injetadas após o DOMContentLoaded
        const tryApply = (attempt)=>{
            try{ console.debug && console.debug('loadGroups tryApply attempt', attempt); }catch(e){}
            const tbody = table.tBodies[0];
            if(!tbody){
                try{ console.debug && console.debug('loadGroups tbody not ready, will retry', attempt); }catch(e){}
                if(attempt < 5) setTimeout(()=> tryApply(attempt+1), 150);
                return;
            }
            let matchedAny = false;
            for(const g of groups){
                if(!g.ids || !g.name) continue;
                for(const id of g.ids){
                    const row = tbody.querySelector('tr[data-tx-id="' + id + '"]');
                    if(row){
                        row.classList.add('row-grouped');
                        row.setAttribute('data-group-name', g.name);
                        matchedAny = true;
                        try{ console.debug && console.debug('loadGroups applied id', id, 'group', g.name); }catch(e){}
                    }
                }
            }
            // Antes de tentar aplicar grupos, carregar os grupos ocultos para esta página e aplicar a classe de oculto às linhas correspondentes. Isso garante que as linhas pertencentes a grupos ocultos sejam ocultadas mesmo que o grupo em si não seja encontrado (por exemplo, se o grupo foi salvo mas as linhas foram alteradas).
            try{
                const hiddenNames = loadHiddenGroups(table);
                if(Array.isArray(hiddenNames) && hiddenNames.length){
                    try{ console.debug && console.debug('loadGroups applying hidden groups', hiddenNames); }catch(e){}
                    for(const name of hiddenNames){
                        for(const g of groups){
                            if(g.name === name && Array.isArray(g.ids)){
                                for(const id of g.ids){
                                    const row = tbody.querySelector('tr[data-tx-id="' + id + '"]');
                                    if(row){ row.classList.add('row-hidden'); row.classList.add('row-hidden-by-group'); }
                                }
                            }
                        }
                    }
                }
            }catch(e){ console.error('loadGroups apply hiddenGroups', e); }
            // Se não conseguiu aplicar nenhum grupo, pode ser que as linhas ainda não estejam no DOM (por exemplo, carregamento assíncrono). Tentar novamente algumas vezes antes de desistir.
            if(!matchedAny && attempt < 5){
                try{ console.debug && console.debug('loadGroups no matches yet, retrying', attempt); }catch(e){}
                setTimeout(()=> tryApply(attempt+1), 150);
            }
        };

        tryApply(0);
        return groups;
    }catch(e){ console.error('loadGroups error', e); return []; }
}

function hiddenGroupsKey(table){
    try{
        let pageKey = table && table.dataset && table.dataset.pageKey ? table.dataset.pageKey : window.location.pathname;
        try{
            if(String(pageKey).includes('mes_atual')){
                const now = new Date();
                try{
                    const raw = sessionStorage.getItem('next_month_view');
                    if(raw){
                        const cfg = JSON.parse(raw);
                        if(cfg && cfg.active && typeof cfg.day === 'number'){
                            if(now.getDate() > cfg.day){ now.setMonth(now.getMonth() + 1); }
                        }
                    }
                }catch(e){}
                const yyyy = now.getFullYear();
                const mm = String(now.getMonth() + 1).padStart(2,'0');
                pageKey = String(pageKey).replace(/mes_atual/g, `${yyyy}/${mm}/`);
            }
        }catch(e){}
        const key = 'myfinance:hiddenGroups:' + pageKey;
        try{ console.debug && console.debug('hiddenGroupsKey ->', key); }catch(e){}
        return key;
    }catch(e){ return 'myfinance:hiddenGroups:' + window.location.pathname; }
}

function saveHiddenGroups(table, names){
    try{
        const k = hiddenGroupsKey(table);
        localStorage.setItem(k, JSON.stringify(Array.isArray(names)?names:[]));
        try{ console.debug && console.debug('saveHiddenGroups', k, names); }catch(e){}
    }catch(e){ console.error('saveHiddenGroups error', e); }
}

function loadHiddenGroups(table){
    try{
        const k = hiddenGroupsKey(table);
        const raw = localStorage.getItem(k);
        try{ console.debug && console.debug('loadHiddenGroups', k, raw); }catch(e){}
        if(!raw) return [];
        const arr = JSON.parse(raw || '[]');
        return Array.isArray(arr) ? arr : [];
    }catch(e){ console.error('loadHiddenGroups error', e); return []; }
}

function saveGroup(table, name){
    try{
        const tbody = table.tBodies[0];
        if(!tbody) return;
        const ids = Array.from(tbody.rows).map(r => r.querySelector('td.checkbox-cell input[type="checkbox"]') ? r : null).filter(Boolean)
            .map(r => r.getAttribute('data-tx-id')).filter(Boolean).filter(id=>{
                const row = tbody.querySelector('tr[data-tx-id="' + id + '"]');
                return row && row.querySelector('td.checkbox-cell input[type="checkbox"]') && row.querySelector('td.checkbox-cell input[type="checkbox"]').checked;
            });
        if(!ids.length) return;
        // persist group
        const raw = localStorage.getItem(groupsStorageKey(table));
        const groups = raw ? JSON.parse(raw) : [];
        const idx = groups.findIndex(g => g.name === name);
        if(idx !== -1){
            const overwrite = window.confirm('Já existe um grupo com este nome nesta página. Deseja sobrescrever?');
            if(!overwrite) return false;
            groups[idx] = { name: name, ids: ids, createdAt: (new Date()).toISOString() };
        } else {
            groups.push({ name: name, ids: ids, createdAt: (new Date()).toISOString() });
        }
        const gKey = groupsStorageKey(table);
        localStorage.setItem(gKey, JSON.stringify(groups));
        try{ console.info && console.info('saveGroup saved key', gKey, 'groupsCount', groups.length); }catch(e){}
        // mark rows
        for(const id of ids){
            const row = tbody.querySelector('tr[data-tx-id="' + id + '"]');
            if(row){ row.classList.add('row-grouped'); row.setAttribute('data-group-name', name); }
        }
        // update popup groups list if visible
        const popup = document.querySelector('.myfinance-checkbox-popup');
        if(popup){
            const gc = popup.querySelector('.myfinance-groups-list');
            if(gc && gc.style.display !== 'none') renderGroupsList(gc, table);
        }
        return true;
    }catch(e){ console.error('saveGroup error', e); }
    return false;
}

// Helper para atualizar o ícone do toggle principal (eye/eye-slash) com base na presença de linhas ocultas, usado após ações que podem alterar o estado de oculto das linhas.
function updateMainToggleIcon(table, toggleBtn){
    try{
        const anyHidden = table.querySelector('tbody tr.row-hidden') !== null;
        setToggleIcon(toggleBtn, anyHidden);
    }catch(e){ }
}

function hideGroups(table){
    try{
        const tbody = table.tBodies[0];
        if(!tbody) return;
        const rows = Array.from(tbody.querySelectorAll('tr.row-grouped'));
        const applied = [];
        const groupNames = new Set();
        for(const row of rows){
            row.classList.add('row-hidden');
            row.classList.add('row-hidden-by-group');
            const id = row.getAttribute('data-tx-id') || null;
            const gname = row.getAttribute('data-group-name') || null;
            if(id) applied.push(id);
            if(gname) groupNames.add(gname);
        }
        try{ console.debug && console.debug('hideGroups applied ids', applied); }catch(e){}
        // Persistir os grupos ocultos para reaplicar a ocultação mesmo após navegação ou recarregamento da página
        try{ saveHiddenGroups(table, Array.from(groupNames)); }catch(e){}
        refreshZebra(table);
        recalcDashboardTotals(table);
        showToast('Grupos ocultados', 'success');
        // Atualizar ícone do toggle principal
        const toggleBtn = document.getElementById('toggle-checkboxes'); if(toggleBtn) updateMainToggleIcon(table, toggleBtn);
        const popup = document.querySelector('.myfinance-checkbox-popup');
        if(popup){ const hd = popup.querySelector('.myfinance-hidden-descriptions'); if(hd && hd.style.display !== 'none') renderHiddenDescriptions(); }
    }catch(e){ console.error('hideGroups error', e); }
}

/* Agrupamento de linhas por grupos */
function getGroupsFromStorage(table){
    try{
        const raw = localStorage.getItem(groupsStorageKey(table));
        if(!raw) return [];
        const groups = JSON.parse(raw || '[]');
        return Array.isArray(groups) ? groups : [];
    }catch(e){ console.error('getGroupsFromStorage', e); return []; }
}

function saveGroupsToStorage(groups, table){
    try{ localStorage.setItem(groupsStorageKey(table), JSON.stringify(groups || [])); }catch(e){ console.error('saveGroupsToStorage', e); }
}

function renderGroupsList(container, table){
    // Container: elemento onde a lista será renderizada (criado pelo popup)
    if(!container) return;
    // Limpar conteúdo existente
    container.innerHTML = '';

    const groups = getGroupsFromStorage(table);
    if(!groups.length){
        const empty = document.createElement('div'); empty.className = 'myfinance-groups-empty';
        empty.textContent = 'Nenhum grupo salvo';
        container.appendChild(empty);
        return;
    }

    for(const g of groups){
        const row = document.createElement('div'); row.className = 'myfinance-group-item';
        const label = document.createElement('span'); label.className = 'myfinance-group-name';
        label.textContent = g.name + ' (' + (Array.isArray(g.ids)?g.ids.length:0) + ')';
        row.appendChild(label);

        // icon-only controls aligned to the right
        const icons = document.createElement('div');
        icons.style.display = 'flex';
        icons.style.gap = '8px';
        icons.style.marginLeft = 'auto';

        const icHide = document.createElement('i'); icHide.className = 'fa-solid fa-eye-slash myfinance-group-hide'; icHide.title='Ocultar grupo'; icHide.style.cursor='pointer';
        icHide.addEventListener('click', function(){ hideGroupByName(table, g.name); setToggleIcon(document.getElementById('toggle-checkboxes'), true); });
        icons.appendChild(icHide);

        const icShow = document.createElement('i'); icShow.className = 'fa-solid fa-eye myfinance-group-show'; icShow.title='Mostrar grupo'; icShow.style.cursor='pointer';
        icShow.addEventListener('click', function(){ showGroupByName(table, g.name); setToggleIcon(document.getElementById('toggle-checkboxes'), false); });
        icons.appendChild(icShow);

        const icDel = document.createElement('i'); icDel.className = 'fa-solid fa-trash myfinance-group-delete'; icDel.title='Remover grupo'; icDel.style.cursor='pointer'; icDel.style.color = 'inherit';
        icDel.addEventListener('click', function(){ deleteGroupByName(table, g.name, container.closest('.myfinance-checkbox-popup')); });
        icons.appendChild(icDel);

        row.appendChild(icons);

        container.appendChild(row);
    }
}

function hideGroupByName(table, name){
    try{
        const groups = getGroupsFromStorage(table);
        const g = groups.find(x => x.name === name);
        if(!g || !Array.isArray(g.ids)) return;
        const tbody = table.tBodies[0];
        const applied = [];
        for(const id of g.ids){
            const row = tbody.querySelector('tr[data-tx-id="' + id + '"]');
            if(row){ row.classList.add('row-hidden'); applied.push(id); }
            else { try{ console.debug && console.debug('hideGroupByName missing row for id', id, 'group', name); }catch(e){} }
        }
        try{ console.debug && console.debug('hideGroupByName applied ids', applied, 'for group', name); }catch(e){}
        // Adicionar ao hiddenGroups storage para reaplicar ocultação mesmo após navegação
        try{
            const hidden = loadHiddenGroups(table);
            if(!hidden.includes(name)){
                hidden.push(name);
                saveHiddenGroups(table, hidden);
            }
        }catch(e){ console.error('hideGroupByName saveHiddenGroups', e); }
        refreshZebra(table);
        recalcDashboardTotals(table);
        saveHiddenRows(table);
    }catch(e){ console.error('hideGroupByName', e); }
}

function showGroupByName(table, name){
    try{
        const groups = getGroupsFromStorage(table);
        const g = groups.find(x => x.name === name);
        if(!g || !Array.isArray(g.ids)) return;
        const tbody = table.tBodies[0];
        const applied = [];
        for(const id of g.ids){
            const row = tbody.querySelector('tr[data-tx-id="' + id + '"]');
            if(row){
                // Remover apenas a classe de ocultação por grupo, mantendo a ocultação manual se presente (o usuário pode ter ocultado manualmente algumas linhas do grupo, e não queremos revelar essas linhas acidentalmente)
                row.classList.remove('row-hidden-by-group');
                if(!row.classList.contains('row-hidden-by-manual')) row.classList.remove('row-hidden');
                // Assegurar que o checkbox da linha esteja desmarcado para evitar confusão visual (o usuário pode ter marcado o checkbox para ocultar, mas ao mostrar o grupo queremos limpar esse estado para evitar que a linha seja ocultada novamente acidentalmente se o usuário clicar em "Ocultar" sem perceber que o checkbox ainda está marcado)
                try{
                    const cb = row.querySelector('td.checkbox-cell input[type="checkbox"], input[type="checkbox"]');
                    if(cb) cb.checked = false;
                }catch(e){}
                applied.push(id);
            } else { try{ console.debug && console.debug('showGroupByName missing row for id', id, 'group', name); }catch(e){} }
        }
        try{ console.debug && console.debug('showGroupByName applied ids', applied, 'for group', name); }catch(e){}
        // Remover do hiddenGroups storage
        try{
            const hidden = loadHiddenGroups(table);
            const idx = hidden.indexOf(name);
            if(idx !== -1){ hidden.splice(idx,1); saveHiddenGroups(table, hidden); }
        }catch(e){ console.error('showGroupByName saveHiddenGroups', e); }
        try{ updateSelectAllState(table); }catch(e){}
        refreshZebra(table);
        recalcDashboardTotals(table);
        saveHiddenRows(table);
        const toggleBtn = document.getElementById('toggle-checkboxes'); if(toggleBtn) updateMainToggleIcon(table, toggleBtn);
        const popup = document.querySelector('.myfinance-checkbox-popup');
        if(popup){ const hd = popup.querySelector('.myfinance-hidden-descriptions'); if(hd && hd.style.display !== 'none') renderHiddenDescriptions(); }
    }catch(e){ console.error('showGroupByName', e); }
}

function deleteGroupByName(table, name, popup){
    try{
        const groups = getGroupsFromStorage(table);
        const idx = groups.findIndex(x => x.name === name);
        if(idx === -1) return;
        const removed = groups.splice(idx,1)[0];
        saveGroupsToStorage(groups, table);
        // cleanup DOM markers
        const tbody = table.tBodies[0];
        for(const id of (removed.ids||[])){
            const row = tbody.querySelector('tr[data-tx-id="' + id + '"]');
            if(row){ row.classList.remove('row-grouped'); row.removeAttribute('data-group-name'); }
        }
        // Renderizar lista de grupos no popup se estiver aberto
        if(popup){
            const gc = popup.querySelector('.myfinance-groups-list');
            if(gc) renderGroupsList(gc, table);
            const hd = popup.querySelector('.myfinance-hidden-descriptions'); if(hd && hd.style.display !== 'none') renderHiddenDescriptions();
        }
    }catch(e){ console.error('deleteGroupByName', e); }
}

function refreshZebra(table){
    try{
        const tbody = table.tBodies[0];
        if(!tbody) return;
        const rows = Array.from(tbody.rows).filter(r => !r.classList.contains('row-hidden'));
        // Remover classes zebra existentes
        Array.from(tbody.rows).forEach(r => { r.classList.remove('zebra-odd','zebra-even'); });
        let i = 0;
        for(const r of rows){
            const cls = (i % 2 === 0) ? 'zebra-even' : 'zebra-odd';
            r.classList.add(cls);
            i++;
        }
    }catch(e){ console.error('refreshZebra error', e); }
}

function setToggleIcon(toggleBtn, hidden){
    // hidden === true => eye-slash; false => eye
    const icon = toggleBtn.querySelector('i.fa-solid');
    if(!icon) return;
    if(hidden){
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
    } else {
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
    }
}

/* Persistence helpers */
function storageKeyForPage(table){
    try{
        let pageKey = table && table.dataset && table.dataset.pageKey ? table.dataset.pageKey : window.location.pathname;
        try{
            if(String(pageKey).includes('mes_atual')){
                const now = new Date();
                try{
                    const raw = sessionStorage.getItem('next_month_view');
                    if(raw){
                        const cfg = JSON.parse(raw);
                        if(cfg && cfg.active && typeof cfg.day === 'number'){
                            if(now.getDate() > cfg.day){
                                now.setMonth(now.getMonth() + 1);
                            }
                        }
                    }
                }catch(e){}
                const yyyy = now.getFullYear();
                const mm = String(now.getMonth() + 1).padStart(2,'0');
                pageKey = String(pageKey).replace(/mes_atual/g, `${yyyy}/${mm}/`);
            }
        }catch(e){}
        const key = 'myfinance:hiddenRows:' + pageKey;
        try{ console.debug && console.debug('storageKeyForPage ->', key); }catch(e){}
        return key;
    }catch(e){ return 'myfinance:hiddenRows:' + window.location.pathname; }
}

function saveHiddenRows(table){
    try{
        const tbody = table.tBodies[0];
        if(!tbody) return;
        const ids = Array.from(tbody.rows).filter(r => r.classList.contains('row-hidden') && r.classList.contains('row-hidden-by-manual')).map(r => r.getAttribute('data-tx-id')).filter(Boolean);
        if(ids.length) localStorage.setItem(storageKeyForPage(table), JSON.stringify(ids));
        else localStorage.removeItem(storageKeyForPage(table));
    }catch(e){ console.error('saveHiddenRows error', e); }
}

function loadHiddenRows(table){
    try{
        const key = storageKeyForPage(table);
        try{ console.debug && console.debug('loadHiddenRows key', key); }catch(e){}
        const raw = localStorage.getItem(key);
        if(!raw) return false;
        const ids = JSON.parse(raw || '[]');
        try{ console.debug && console.debug('loadHiddenRows ids', ids); }catch(e){}
        if(!Array.isArray(ids) || !ids.length) return false;
        const tbody = table.tBodies[0];
        if(!tbody) return false;
        let any = false;
        for(const id of ids){
            const row = tbody.querySelector('tr[data-tx-id="' + id + '"]');
            if(row){ row.classList.add('row-hidden'); row.classList.add('row-hidden-by-manual'); any = true; }
        }
        return any;
    }catch(e){ console.error('loadHiddenRows error', e); return false; }
}

function clearHiddenRows(table){
    try{ localStorage.removeItem(storageKeyForPage(table)); }catch(e){ console.error('clearHiddenRows error', e); }
}
