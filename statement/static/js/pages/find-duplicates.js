(function(){
    const table = document.getElementById('statement-table');
    if(!table) return;
    const btn = document.getElementById('mark-duplicates');
    if(!btn) return;

    function clearHighlights(){
        Array.from(table.tBodies[0].rows).forEach(r => r.classList.remove('duplicate-highlight'));
    }

    function markDuplicates(){
        clearHighlights();
        const rows = Array.from(table.tBodies[0].rows).filter(r => !r.classList.contains('group-header') && !r.classList.contains('group-total-row'));
        const map = new Map();
        rows.forEach(r => {
            const user = r.dataset.dupUser || '';
            const app = (r.dataset.dupApp || '').trim();
            const title = (r.dataset.duptitle || r.dataset.dupTitle || '').trim();
            const message = (r.dataset.dupMessage || r.dataset.dupmesssage || '').trim();
            const created = (r.dataset.dupCreated_at || r.dataset.dupCreatedAt || r.dataset.dupCreated || r.dataset.dupCreated_At || r.dataset.dupCreatedAt) || r.dataset.dupCreated_at || '';
            // normalize key
            const key = [user, app, title, message, created].map(s => (s||'').toString().trim()).join('||');
            if(!map.has(key)) map.set(key, []);
            map.get(key).push(r);
        });

        for(const [k, group] of map.entries()){
            if(group.length > 1){
                group.forEach(r => r.classList.add('duplicate-highlight'));
            }
        }
    }

    btn.addEventListener('click', function(){
        markDuplicates();
    });
    // allow keyboard
    btn.addEventListener('keydown', function(e){ if(e.key==='Enter' || e.key===' '){ e.preventDefault(); markDuplicates(); } });
})();
