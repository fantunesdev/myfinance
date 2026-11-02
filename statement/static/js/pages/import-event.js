const eventLabels = {
    purchase: 'Compra',
    fixed_expense: 'Despesa fixa',
    card_payment: 'Pagamento da fatura',
    refund: 'Estorno',
    unknown: 'Não identificado',
};

export function renderEventType(cell, transaction) {
    const container = document.createElement('div');
    container.className = 'import-event-type';
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

    if (transaction.review_reason) {
        const notice = document.createElement('small');
        notice.textContent = transaction.review_reason;
        container.appendChild(notice);
    }
    cell.appendChild(container);
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
        fixed: (Object.hasOwn(eventLabels, chosen) ? chosen : original.event_type) === 'fixed_expense',
    };
}
