const eventLabels = {
    purchase: 'Compra',
    card_payment: 'Pagamento da fatura',
    refund: 'Estorno',
    unknown: 'Revisar evento',
};

export function renderEventReview(cell, transaction) {
    const container = document.createElement('div');
    container.className = 'import-event-review';
    const event = document.createElement('select');
    event.id = `id_event_type_${transaction.id}`;
    event.className = 'form-control input-sm';
    event.setAttribute('aria-label', 'Tipo de evento');
    for (const [value, label] of Object.entries(eventLabels)) {
        const option = document.createElement('option');
        option.value = value;
        option.textContent = label;
        event.appendChild(option);
    }
    event.value = transaction.event_type || 'unknown';
    container.appendChild(event);

    const action = document.createElement('select');
    action.id = `id_event_action_${transaction.id}`;
    action.className = 'form-control input-sm';
    action.setAttribute('aria-label', 'Tratamento do evento');
    for (const [value, label] of [['review', 'Revisar'], ['import', 'Cadastrar'], ['ignore', 'Ignorar']]) {
        const option = document.createElement('option');
        option.value = value;
        option.textContent = label;
        action.appendChild(option);
    }
    action.value = transaction.needs_review ? 'review' : 'import';
    action.addEventListener('change', () => {
        const checkbox = document.getElementById(String(transaction.id));
        if (checkbox && !checkbox.disabled) {
            checkbox.checked = action.value === 'import';
            checkbox.dispatchEvent(new Event('change'));
        }
    });
    container.appendChild(action);
    if (transaction.review_reason) {
        const notice = document.createElement('small');
        notice.textContent = transaction.review_reason;
        container.appendChild(notice);
    }
    cell.appendChild(container);
}

export function importAction(id) {
    return document.getElementById(`id_event_action_${id}`)?.value || 'import';
}

export function eventMetadata(id, original = {}) {
    const chosen = document.getElementById(`id_event_type_${id}`)?.value;
    return {
        original_description: original.original_description || '',
        merchant_description: original.source_type === 'notification' ? original.merchant_description || '' : original.merchant_description || original.original_description || original.description || '',
        source_type: original.source_type || '',
        source_app: original.source_app || '',
        source_category: original.source_category || '',
        source_notification: original.source_notification || original.notification_id || null,
        event_type: Object.hasOwn(eventLabels, chosen) ? chosen : original.event_type || 'unknown',
    };
}
