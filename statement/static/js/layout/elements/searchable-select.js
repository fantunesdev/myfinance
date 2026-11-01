const alphabetical = new Intl.Collator('pt-BR', { sensitivity: 'base' });
const normalize = value => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
const hasValue = option => option.value !== '' && option.value !== '0';

export function enhanceSearchableSelect(select) {
    const search = document.getElementById(`${select.id}_search`);
    const results = document.getElementById(`${select.id}_results`);
    if (!search || !results) return null;

    const picker = search.parentElement;
    const required = select.required;
    let matches = [];
    let resultNodes = [];
    let activeIndex = -1;

    function close() {
        results.hidden = true;
        search.setAttribute('aria-expanded', 'false');
        search.removeAttribute('aria-activedescendant');
    }

    function refresh() {
        const selectedValue = select.value;
        const options = [...select.options].sort((a, b) => {
            if (hasValue(a) !== hasValue(b)) return hasValue(a) ? 1 : -1;
            return alphabetical.compare(a.textContent, b.textContent);
        });
        select.replaceChildren(...options);
        select.value = selectedValue;
        const selected = options.find(option => hasValue(option) && option.value === select.value);
        search.value = selected?.textContent || '';
        search.disabled = select.disabled;
        search.setCustomValidity(required && !selected ? 'Selecione uma opção da lista.' : '');
        close();
    }

    function highlight(index) {
        activeIndex = index;
        resultNodes.forEach((node, i) => node.setAttribute('aria-selected', String(i === index)));
        if (resultNodes[index]) search.setAttribute('aria-activedescendant', resultNodes[index].id);
        else search.removeAttribute('aria-activedescendant');
        resultNodes[index]?.scrollIntoView?.({ block: 'nearest' });
    }

    function choose(option) {
        select.value = option.value;
        select.dispatchEvent(new Event('change', { bubbles: true }));
        search.focus();
        close();
    }

    function showResults(query = '') {
        if (search.disabled) return;
        const term = normalize(query.trim());
        matches = [...select.options].filter(option =>
            hasValue(option) && !option.disabled && normalize(option.textContent).includes(term)
        );
        results.replaceChildren();
        resultNodes = matches.map(option => {
            const node = document.createElement('li');
            node.id = `${select.id}_option_${option.value}`;
            node.setAttribute('role', 'option');
            node.textContent = option.textContent;
            node.addEventListener('mousedown', event => event.preventDefault());
            node.addEventListener('click', () => choose(option));
            results.appendChild(node);
            return node;
        });
        if (!matches.length) {
            const empty = document.createElement('li');
            empty.className = 'searchable-select-empty';
            empty.setAttribute('role', 'presentation');
            empty.textContent = results.dataset.emptyMessage;
            results.appendChild(empty);
        }
        results.hidden = false;
        search.setAttribute('aria-expanded', 'true');
        const selectedIndex = matches.findIndex(option => option.value === select.value);
        highlight(matches.length ? Math.max(selectedIndex, 0) : -1);
    }

    search.required = required;
    select.required = false;
    select.hidden = true;
    search.hidden = false;
    if (select.labels[0]) select.labels[0].htmlFor = search.id;
    search.addEventListener('focus', () => {
        search.select();
        showResults();
    });
    search.addEventListener('click', () => { if (results.hidden) showResults(); });
    search.addEventListener('input', () => {
        search.setCustomValidity('Selecione uma opção da lista.');
        showResults(search.value);
    });
    search.addEventListener('keydown', event => {
        if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
            event.preventDefault();
            if (results.hidden) {
                showResults();
                if (event.key === 'ArrowUp') highlight(matches.length - 1);
            } else if (matches.length) {
                highlight(Math.max(0, Math.min(matches.length - 1, activeIndex + (event.key === 'ArrowDown' ? 1 : -1))));
            }
        } else if (event.key === 'Enter') {
            event.preventDefault();
            if (!results.hidden && matches[activeIndex]) choose(matches[activeIndex]);
            else showResults(search.value);
        } else if (event.key === 'Escape') {
            event.preventDefault();
            refresh();
        }
    });
    picker.addEventListener('focusout', event => {
        if (!picker.contains(event.relatedTarget)) refresh();
    });
    select.addEventListener('change', refresh);
    refresh();
    return { refresh };
}
