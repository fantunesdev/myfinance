(function(){
    const table = document.getElementById('statement-table');
    if(!table) return;

    // elementos
    const selMonth = document.getElementById('notif-month');
    const selYear = document.getElementById('notif-year');
    const btnPrev = document.getElementById('notif-prev');
    const btnNext = document.getElementById('notif-next');

    // month names
    const months = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];

    // coleta datas disponíveis nas linhas e anexa data-iso em cada row
    const rows = Array.from(table.tBodies[0].rows);
    const years = new Set();
    rows.forEach(r => {
        // procura por uma data no formato dd/mm/yyyy
        const match = r.innerText.match(/(\d{1,2})\/(\d{1,2})\/(\d{4})/);
        if(match){
            const d = new Date(parseInt(match[3],10), parseInt(match[2],10)-1, parseInt(match[1],10));
            r.dataset.createdAt = d.toISOString();
            years.add(d.getFullYear());
        }
    });

    // popula selects
    months.forEach((m,i)=>{
        const opt = document.createElement('option');
        opt.value = i+1;
        opt.text = m;
        selMonth.appendChild(opt);
    });

    // adiciona opção 'Todos' no topo para permitir limpar filtro de mês
    const optAllM = document.createElement('option'); optAllM.value = ''; optAllM.text = 'Todos';
    selMonth.insertBefore(optAllM, selMonth.firstChild);

    const sortedYears = Array.from(years).sort((a,b)=>a-b);
    if(sortedYears.length===0){
        // se não houver datas, usa ano atual
        const y = new Date().getFullYear();
        sortedYears.push(y);
    }
    sortedYears.forEach(y=>{
        const opt = document.createElement('option');
        opt.value = y;
        opt.text = y;
        selYear.appendChild(opt);
    });

    // adiciona opção 'Todos' no topo para permitir limpar filtro de ano
    const optAllY = document.createElement('option'); optAllY.value = ''; optAllY.text = 'Todos';
    selYear.insertBefore(optAllY, selYear.firstChild);

    // seta default para o mês/ano mais recente
    const maxYear = Math.max.apply(null, sortedYears);
    selYear.value = maxYear;
    // tenta pegar mês mais recente entre as linhas desse ano
    const monthsInYear = rows.map(r=>{
        if(!r.dataset.createdAt) return null;
        const d = new Date(r.dataset.createdAt);
        return d.getFullYear()===maxYear ? d.getMonth()+1 : null;
    }).filter(x=>x!=null);
    selMonth.value = monthsInYear.length ? Math.max.apply(null, monthsInYear) : (new Date().getMonth()+1);

    function applyMonthYearFilter(){
        const fm = selMonth.value ? parseInt(selMonth.value,10) : null;
        const fy = selYear.value ? parseInt(selYear.value,10) : null;
        // grava no table dataset para que `list-filters.js` também respeite
        if(fm && fy){
            table.dataset.filterMonth = fm;
            table.dataset.filterYear = fy;
        } else {
            // remove filtro para mostrar todas as notificações
            delete table.dataset.filterMonth;
            delete table.dataset.filterYear;
        }
        // dispara re-aplicação dos filtros de coluna se existir
        if(window.myFinance && typeof window.myFinance.triggerApplyFilters === 'function'){
            window.myFinance.triggerApplyFilters();
        } else {
            // fallback: tente chamar applyFilters global se existir
            if(typeof window.applyColumnFilters === 'function') window.applyColumnFilters();
            if(typeof window.applyFilters === 'function') window.applyFilters();
        }
    }

    btnPrev.addEventListener('click', function(){
        let m = parseInt(selMonth.value,10);
        let y = parseInt(selYear.value,10);
        m -= 1;
        if(m<1){ m=12; y -=1; }
        // se ano não existe no select, adiciona
        if(!Array.from(selYear.options).some(o=>parseInt(o.value,10)===y)){
            const opt = document.createElement('option'); opt.value = y; opt.text = y; selYear.appendChild(opt);
        }
        selYear.value = y;
        selMonth.value = m;
        applyMonthYearFilter();
    });

    btnNext.addEventListener('click', function(){
        let m = parseInt(selMonth.value,10);
        let y = parseInt(selYear.value,10);
        m += 1;
        if(m>12){ m=1; y +=1; }
        if(!Array.from(selYear.options).some(o=>parseInt(o.value,10)===y)){
            const opt = document.createElement('option'); opt.value = y; opt.text = y; selYear.appendChild(opt);
        }
        selYear.value = y;
        selMonth.value = m;
        applyMonthYearFilter();
    });

    selMonth.addEventListener('change', applyMonthYearFilter);
    selYear.addEventListener('change', applyMonthYearFilter);

    // botão limpar filtro
    const btnClear = document.getElementById('notif-clear');
    if(btnClear){
        function clearFilter(){
            // remove atributos do dataset e solicita reaplicação
            delete table.dataset.filterMonth;
            delete table.dataset.filterYear;
            // reset visual para 'Todos'
            if(selMonth) selMonth.value = '';
            if(selYear) selYear.value = '';
            if(window.myFinance && typeof window.myFinance.triggerApplyFilters === 'function'){
                window.myFinance.triggerApplyFilters();
            } else {
                const event = new CustomEvent('myfinance:applyFilters'); window.dispatchEvent(event);
            }
        }
        btnClear.addEventListener('click', clearFilter);
        btnClear.addEventListener('keydown', function(e){ if(e.key==='Enter' || e.key===' '){ e.preventDefault(); clearFilter(); } });
    }

    // aplica inicialmente
    applyMonthYearFilter();
})();
