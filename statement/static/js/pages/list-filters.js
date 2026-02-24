(function(){
    const table = document.getElementById('statement-table');
    if (!table) return;
    const tbody = table.tBodies[0];
    const filters = Array.from(table.querySelectorAll('.column-filter'));
    const toggleBtn = document.getElementById('toggle-filters');
    const filterRow = table.querySelector('.filter-row');

    function normalize(text){
        return (text||'').toString().toLowerCase();
    }

    function applyFilters(){
        const values = filters.map(f => normalize(f.value));
        for(const row of tbody.rows){
            // Ignora linhas de cabeçalho de grupo e linhas de total
            if(row.classList.contains('group-header') || row.classList.contains('group-total-row')){
                row.style.display = '';
                continue;
            }
            // Alguns rows podem ter colspans; se não tiver células suficientes, pula
            let visible = true;
            for(let i=0;i<values.length;i++){
                const v = values[i];
                if(!v) continue;
                const cell = row.cells[i];
                if(!cell){ visible = false; break; }
                const cellText = normalize(cell.innerText);
                if(cellText.indexOf(v) === -1){ visible = false; break; }
            }
            // Se a tabela tiver filtros de mês/ano definidos, respeita-os (filtragem client-side)
            const fm = table.dataset.filterMonth ? parseInt(table.dataset.filterMonth,10) : null;
            const fy = table.dataset.filterYear ? parseInt(table.dataset.filterYear,10) : null;
            if(fm && fy){
                // tenta extrair a primeira data no formato dd/mm/YYYY da linha
                const m = (row.dataset.createdAt) ? (new Date(row.dataset.createdAt).getMonth()+1) : null;
                const y = (row.dataset.createdAt) ? (new Date(row.dataset.createdAt).getFullYear()) : null;
                if(m==null || y==null || m !== fm || y !== fy){
                    visible = false;
                }
            }
            row.style.display = visible ? '' : 'none';
        }
    }

    // Se o filtro estiver oculto, ao mostrar ele foca no primeiro campo de filtro para facilitar a digitação
    if(toggleBtn && filterRow){
        toggleBtn.addEventListener('click', function(){
            if(filterRow.style.display === 'table-row'){
                filterRow.style.display = 'none';
            } else {
                filterRow.style.display = 'table-row';
                // focus first filter
                const first = filters[0];
                if(first) first.focus();
            }
        });
    }

    // Para evitar aplicar filtros a cada tecla digitada, usamos um debounce de 120ms
    let debounceTimer = null;
    filters.forEach(f => {
        f.addEventListener('input', function(){
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(applyFilters, 120);
        });
    });

    // Ordenação por coluna (client-side)
    const sortButtons = Array.from(table.querySelectorAll('.sort-btn'));
    if(sortButtons.length){
        // estado de ordenação por coluna: index -> asc/desc
        const sortState = { index: null, asc: true };

        function getCellValue(row, idx){
            const cell = row.cells[idx];
            if(!cell) return '';
            return cell.innerText.trim();
        }

        function isNumeric(n){ return !isNaN(parseFloat(n)) && isFinite(n); }

        function sortByColumn(idx){
            // se houver linhas de grupo, não ordena para evitar quebrar agrupamentos
            const hasGroups = Array.from(tbody.rows).some(r => r.classList.contains('group-header'));
            if(hasGroups) return;

            const rows = Array.from(tbody.rows).filter(r => !r.classList.contains('group-header') && !r.classList.contains('group-total-row'));
            const asc = (sortState.index === idx) ? !sortState.asc : true;
            rows.sort((a,b)=>{
                const va = getCellValue(a, idx);
                const vb = getCellValue(b, idx);
                if(isNumeric(va) && isNumeric(vb)){
                    return asc ? (parseFloat(va) - parseFloat(vb)) : (parseFloat(vb) - parseFloat(va));
                }
                return asc ? va.localeCompare(vb) : vb.localeCompare(va);
            });
            // Reapende rows ordenadas ao tbody
            for(const r of rows) tbody.appendChild(r);

            // atualizar estado e atualizar ícones (usar Font Awesome: fa-sort, fa-sort-up, fa-sort-down)
            sortState.index = idx;
            sortState.asc = asc;
            // reset para o ícone padrão (fa-arrows-up-down) em todos os botões
            sortButtons.forEach(btn => {
                btn.innerHTML = '<i class="fa-solid fa-arrows-up-down action-icon"></i>';
                btn.classList.remove('active');
            });
            const activeBtn = table.querySelector('.sort-btn[data-field="' + idx + '"]');
            if(activeBtn){
                activeBtn.innerHTML = '<i class="fa-solid ' + (asc ? 'fa-sort-up' : 'fa-sort-down') + ' action-icon"></i>';
                activeBtn.classList.add('active');
            }
        }

        sortButtons.forEach(btn => {
            btn.addEventListener('click', function(e){
                const idx = parseInt(this.getAttribute('data-field'));
                if(Number.isNaN(idx)) return;
                sortByColumn(idx);
            });
            // suportar ativação por teclado (Enter / Space)
            btn.addEventListener('keydown', function(e){
                if(e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar'){
                    e.preventDefault();
                    const idx = parseInt(this.getAttribute('data-field'));
                    if(Number.isNaN(idx)) return;
                    sortByColumn(idx);
                }
            });
        });
    }

    // Escuta evento customizado para reaplicar filtros a partir de outros scripts
    if(typeof window !== 'undefined'){
        window.addEventListener('myfinance:applyFilters', function(){
            applyFilters();
        });
    }
})();

// Expor um gatilho global para reaplicar filtros a partir de outros scripts
// Ex: window.myFinance.triggerApplyFilters()
if(typeof window !== 'undefined'){
    window.myFinance = window.myFinance || {};
    window.myFinance.triggerApplyFilters = function(){
        try{
            // chama a função interna que aplica filtros
            // localizar e executar applyFilters se estiver no escopo (via IIFE closure)
            // Como applyFilters está no escopo da IIFE, precisamos reimplementar uma
            // pequena rotina que dispara evento customizado para que a IIFE possa reagir.
            // Simples: disparamos um evento 'myfinance:applyFilters' que a IIFE pode ouvir.
            const event = new CustomEvent('myfinance:applyFilters');
            window.dispatchEvent(event);
        }catch(e){
            // fallback: nada além de log
            console.error('triggerApplyFilters error', e);
        }
    };
}
