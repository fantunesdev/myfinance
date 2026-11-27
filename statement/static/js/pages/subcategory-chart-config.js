import { enhanceSearchableSelect } from '../layout/elements/searchable-select.js';

let nextRow = 0;

window.initializeChartPreferences = function(root = document) {
    for (const editor of root.querySelectorAll('[data-chart-editor]')) {
        if (editor.dataset.initialized) continue;
        editor.dataset.initialized = 'true';
        const rows = editor.querySelector('[data-chart-rows]');
        const add = editor.querySelector('[data-chart-add]');
        const empty = editor.querySelector('[data-chart-empty]');
        const status = editor.querySelector('[data-chart-status]');
        const pickers = new Map();

        function refresh(changed = false) {
            const selects = [...rows.querySelectorAll('select')];
            const chosen = new Set(selects.map(select => select.value).filter(Boolean));
            for (const select of selects) {
                for (const option of select.options) {
                    option.disabled = Boolean(option.value && option.value !== select.value && chosen.has(option.value));
                }
                pickers.get(select)?.refresh();
                const selected = [...select.options].find(option => option.value === select.value);
                select.closest('[data-chart-row]').querySelector('label').textContent = selected?.dataset.group || 'Subcategoria';
            }
            const count = chosen.size;
            empty.hidden = selects.length > 0;
            const total = editor.querySelector('template').content.querySelectorAll('option[value]').length - 1;
            add.disabled = selects.some(select => !select.value) || count >= total;
            if (changed) {
                status.textContent = `${count} subcategoria${count === 1 ? '' : 's'} para ocultar. Salve para aplicar.`;
                editor.closest('details').querySelector('[data-chart-summary]').textContent = `${count} para ocultar · alterações não salvas`;
            }
        }

        function initializeRow(row) {
            const select = row.querySelector('select');
            pickers.set(select, enhanceSearchableSelect(select));
        }
        rows.querySelectorAll('[data-chart-row]').forEach(initializeRow);
        rows.addEventListener('change', () => refresh(true));
        rows.addEventListener('click', event => {
            const remove = event.target.closest('[data-chart-remove]');
            if (!remove) return;
            const row = remove.closest('[data-chart-row]');
            pickers.delete(row.querySelector('select'));
            row.remove();
            refresh(true);
            add.focus();
        });
        add.addEventListener('click', () => {
            const fragment = editor.querySelector('[data-chart-row-template]').content.cloneNode(true);
            const row = fragment.querySelector('[data-chart-row]');
            const select = row.querySelector('select');
            select.id = `chart-subcategory-added-${++nextRow}`;
            row.querySelector('label').htmlFor = select.id;
            const search = row.querySelector('[role=combobox]');
            search.id = `${select.id}_search`;
            search.setAttribute('aria-controls', `${select.id}_results`);
            row.querySelector('[role=listbox]').id = `${select.id}_results`;
            rows.append(fragment);
            initializeRow(row);
            refresh();
            search.focus();
        });
        refresh();
    }
};

window.initializeChartPreferences();
