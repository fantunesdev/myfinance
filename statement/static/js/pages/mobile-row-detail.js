const interactiveSelector = 'a, button, input, select, textarea, label, [role="button"], .sort-btn';
const metadataRowClasses = ['group-header', 'group-total-row', 'group-empty'];
const mobileDetailContainers = '.simple-mobile, .dream-mobile, [data-mobile-row-detail]';

export function isMobileDetailNavigationEnabled(table, win = window) {
    return Boolean(
        table
        && table.closest(mobileDetailContainers)
        && win.matchMedia
        && win.matchMedia('(max-width: 600px)').matches
    );
}

export function shouldIgnoreRowClick(target, row) {
    return Boolean(
        !row
        || metadataRowClasses.some(className => row.classList.contains(className))
        || target.closest(interactiveSelector)
    );
}

export function initMobileRowDetailNavigation(doc = document, win = window) {
    const tables = doc.querySelectorAll('#statement-table, [data-mobile-row-detail-table]');

    tables.forEach(table => {
        table.addEventListener('click', event => {
            const row = event.target.closest('tbody tr[data-detail-url]');
            if (!row || !table.contains(row)) return;
            if (!isMobileDetailNavigationEnabled(table, win)) return;
            if (shouldIgnoreRowClick(event.target, row)) return;

            win.location.href = row.dataset.detailUrl;
        });
    });
}

export function updateMobileShortDates(doc = document, win = window) {
    if (!win.matchMedia) return;

    const isMobile = win.matchMedia('(max-width: 600px)').matches;

    doc.querySelectorAll('[data-mobile-date]').forEach(cell => {
        const original = cell.dataset.mobileDate || cell.textContent.trim();
        const shortDate = original.includes('/') && original.split('/').length === 3
            ? original.replace(/^(\d{2})\/(\d{2})\/(\d{4})$/, '$1/$2')
            : original;

        cell.textContent = isMobile ? shortDate : original;
    });
}

if (typeof document !== 'undefined' && typeof window !== 'undefined') {
    initMobileRowDetailNavigation();
    updateMobileShortDates();
    window.addEventListener('resize', () => updateMobileShortDates());
}
