(() => {
    const typeSelect = document.getElementById('id_asset_type');
    const select = document.getElementById('id_investment');
    const optionsElement = document.getElementById('investment-destination-options');
    if (!typeSelect || !select || !optionsElement) return;
    const options = JSON.parse(optionsElement.textContent);
    const destinations = [...select.options].filter(option => option.value).map(option => option.cloneNode(true));
    const search = document.getElementById('investment-destination-search');
    const results = document.getElementById('investment-destination-results');
    const picker = document.getElementById('investment-destination-picker');
    let confirmedValue = select.value;
    let matches = [];
    let resultNodes = [];
    let activeIndex = -1;
    const normalize = value => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();

    function closeResults() {
        if (!search) return;
        results.hidden = true;
        search.setAttribute('aria-expanded', 'false');
        search.removeAttribute('aria-activedescendant');
    }

    function syncSearch() {
        confirmedValue = select.value;
        if (!search) return;
        search.disabled = select.disabled;
        search.placeholder = select.disabled ? select.options[0].textContent : 'Digite para buscar um investimento';
        search.value = [...select.options].find(option => option.value && option.value === select.value)?.textContent || '';
        search.setCustomValidity(select.value ? '' : 'Selecione um investimento da lista.');
        closeResults();
    }

    function highlight(index) {
        activeIndex = index;
        resultNodes.forEach((node, i) => node.setAttribute('aria-selected', String(i === index)));
        if (resultNodes[index]) search.setAttribute('aria-activedescendant', resultNodes[index].id);
        else search.removeAttribute('aria-activedescendant');
    }

    function choose(option) {
        select.value = option.value;
        select.dispatchEvent(new Event('change', { bubbles: true }));
        search.focus();
        closeResults();
    }

    function showResults(query = '') {
        if (!search || search.disabled) return;
        const term = normalize(query.trim());
        matches = [...select.options].filter(option => option.value && normalize(option.textContent).includes(term));
        results.replaceChildren();
        resultNodes = matches.map(option => {
            const node = document.createElement('li');
            node.id = `investment-destination-option-${option.value}`;
            node.setAttribute('role', 'option');
            node.tabIndex = -1;
            node.textContent = option.textContent;
            node.addEventListener('mousedown', event => event.preventDefault());
            node.addEventListener('click', () => choose(option));
            results.appendChild(node);
            return node;
        });
        if (!matches.length) {
            const empty = document.createElement('li');
            empty.className = 'investment-destination-no-results';
            empty.setAttribute('role', 'presentation');
            empty.textContent = 'Nenhum investimento encontrado.';
            results.appendChild(empty);
        }
        results.hidden = false;
        search.setAttribute('aria-expanded', 'true');
        const selected = matches.findIndex(option => option.value === select.value);
        highlight(matches.length ? Math.max(selected, 0) : -1);
    }

    if (search && results && picker) {
        picker.setAttribute('data-searchable', 'true');
        search.required = select.required;
        select.required = false;
        select.hidden = true;
        search.hidden = false;
        document.getElementById('investment-application-label-investment').setAttribute('for', search.id);
        search.addEventListener('focus', () => showResults(select.value ? '' : search.value));
        search.addEventListener('click', () => { if (results.hidden) showResults(select.value ? '' : search.value); });
        search.addEventListener('input', () => {
            select.value = '';
            search.setCustomValidity('Selecione um investimento da lista.');
            showResults(search.value);
        });
        search.addEventListener('keydown', event => {
            if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
                event.preventDefault();
                if (results.hidden) {
                    showResults(select.value ? '' : search.value);
                    if (event.key === 'ArrowUp') highlight(matches.length - 1);
                } else if (matches.length) {
                    highlight(Math.max(0, Math.min(matches.length - 1, activeIndex + (event.key === 'ArrowDown' ? 1 : -1))));
                }
                resultNodes[activeIndex]?.scrollIntoView?.({ block: 'nearest' });
            } else if (event.key === 'Enter') {
                // Picking a destination must never submit the financial form.
                event.preventDefault();
                if (!results.hidden && matches[activeIndex]) choose(matches[activeIndex]);
                else showResults(select.value ? '' : search.value);
            } else if (event.key === 'Escape') {
                event.preventDefault();
                select.value = confirmedValue;
                syncSearch();
            }
        });
        picker.addEventListener('focusout', event => {
            if (!picker.contains(event.relatedTarget)) closeResults();
        });
    }

    function updateFields(changed = false) {
        const investment = options[select.value];
        const showUnits = investment && ['variable_income', 'crypto', 'currency'].includes(investment.asset_type);
        for (const name of ['quantity', 'unit_price']) {
            document.getElementById(`investment-application-field-${name}`).hidden = !showUnits;
            const input = document.getElementById(`id_${name}`);
            input.disabled = !showUnits;
            if (changed || !showUnits) input.value = '';
        }
        if (changed) document.getElementById('id_due_date').value = investment?.due_date || '';
    }
    function filterDestinations(changed = false) {
        const previous = changed ? '' : select.value;
        const matching = destinations.filter(option => options[option.value]?.asset_type === typeSelect.value);
        const placeholder = document.createElement('option');
        placeholder.value = '';
        placeholder.textContent = !typeSelect.value ? 'Selecione o tipo primeiro'
            : matching.length ? 'Selecione o investimento' : 'Nenhum investimento deste tipo';
        select.replaceChildren(placeholder, ...matching.map(option => option.cloneNode(true)));
        select.disabled = !typeSelect.value || !matching.length;
        select.value = matching.some(option => option.value === previous) ? previous : '';
        updateFields(changed);
        syncSearch();
    }
    typeSelect.addEventListener('change', () => filterDestinations(true));
    select.addEventListener('change', () => {
        updateFields(select.value !== confirmedValue);
        syncSearch();
    });
    const amountInput = document.getElementById('id_amount');
    const quantityInput = document.getElementById('id_quantity');
    const unitPriceInput = document.getElementById('id_unit_price');

    function inputNumber(input) {
        if (!input.value.trim()) return NaN;
        if (Number.isFinite(input.valueAsNumber)) return input.valueAsNumber;
        const value = input.value.trim();
        return Number(value.includes(',') ? value.replace(/\./g, '').replace(',', '.') : value);
    }

    function calculateUnitPrice() {
        const amount = inputNumber(amountInput);
        const units = inputNumber(quantityInput);
        if (unitPriceInput.disabled || !Number.isFinite(amount) || !Number.isFinite(units) || amount <= 0 || units <= 0) {
            unitPriceInput.value = '';
            return;
        }
        const price = amount / units;
        const rounded = Number.isFinite(price) ? Number(price.toFixed(6)) : 0;
        unitPriceInput.value = rounded > 0 ? String(rounded) : '';
    }

    amountInput.addEventListener('input', calculateUnitPrice);
    quantityInput.addEventListener('input', calculateUnitPrice);
    filterDestinations();
    if (!unitPriceInput.value) calculateUnitPrice();
})();
