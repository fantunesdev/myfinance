export function setupPhotoReordering(grid) {
    if (!grid) return;
    const status = document.querySelector('.dream-photo-order-status');
    let dragged;
    let originalOrder;
    let dropped = false;
    let saving = false;
    let suppressClickUntil = 0;
    const cards = () => [...grid.querySelectorAll('.dream-photo-card')];

    function notifyOrder() {
        const ordered = cards();
        ordered.forEach((card, index) => {
            const link = card.querySelector('.dream-photo-open');
            link.dataset.photoIndex = index;
            link.setAttribute('aria-label', `Ampliar foto ${index + 1} de ${ordered.length}`);
            const img = link.querySelector('img');
            img.alt = img.alt.replace(/^Foto \d+/, `Foto ${index + 1}`);
            card.querySelector('.dream-photo-remove').setAttribute('aria-label', `Remover foto ${index + 1}`);
        });
        grid.dispatchEvent(new Event('dream-photos-reordered'));
    }

    function restore(order) {
        grid.append(...order);
        notifyOrder();
    }

    async function save(orderBefore) {
        const ordered = cards();
        if (ordered.every((card, index) => card === orderBefore[index])) return;
        saving = true;
        grid.setAttribute('aria-busy', 'true');
        status.hidden = true;
        notifyOrder();
        try {
            const body = new URLSearchParams();
            ordered.forEach((card) => body.append('photo_ids', card.dataset.photoId));
            const response = await fetch(grid.dataset.reorderUrl, {
                method: 'POST',
                headers: { 'X-CSRFToken': document.querySelector('#dream-photo-upload [name=csrfmiddlewaretoken]').value },
                body,
            });
            if (!response.ok || !(await response.json()).saved) throw new Error('Order was not saved');
        } catch {
            restore(orderBefore);
            status.textContent = 'Não foi possível salvar a ordem das fotos. Tente novamente.';
            status.hidden = false;
        } finally {
            saving = false;
            grid.removeAttribute('aria-busy');
        }
    }

    grid.addEventListener('dragstart', (event) => {
        const card = event.target.closest('.dream-photo-card');
        if (!card || saving || event.target.closest('button')) {
            event.preventDefault();
            return;
        }
        dragged = card;
        originalOrder = cards();
        dropped = false;
        event.dataTransfer.effectAllowed = 'move';
        event.dataTransfer.setData('text/plain', card.dataset.photoId);
        card.classList.add('is-dragging');
    });
    grid.addEventListener('dragover', (event) => {
        if (!dragged) return;
        event.preventDefault();
        event.dataTransfer.dropEffect = 'move';
        const target = event.target.closest('.dream-photo-card');
        if (!target || target === dragged) return;
        const bounds = target.getBoundingClientRect();
        const after = event.clientX > bounds.left + bounds.width / 2;
        grid.insertBefore(dragged, after ? target.nextSibling : target);
    });
    grid.addEventListener('drop', (event) => {
        if (!dragged) return;
        event.preventDefault();
        dropped = true;
        suppressClickUntil = Date.now() + 300;
        save(originalOrder);
    });
    grid.addEventListener('dragend', () => {
        if (!dragged) return;
        dragged.classList.remove('is-dragging');
        if (!dropped) restore(originalOrder);
        dragged = null;
    });
    grid.addEventListener('click', (event) => {
        if (Date.now() < suppressClickUntil && event.target.closest('.dream-photo-open')) {
            event.preventDefault();
            event.stopPropagation();
        }
    }, true);
    grid.addEventListener('keydown', (event) => {
        if (!event.altKey || !['ArrowLeft', 'ArrowRight'].includes(event.key) ||
            !event.target.closest('.dream-photo-open')) return;
        event.preventDefault();
        if (saving) return;
        const orderBefore = cards();
        const card = event.target.closest('.dream-photo-card');
        const index = orderBefore.indexOf(card);
        const target = orderBefore[index + (event.key === 'ArrowLeft' ? -1 : 1)];
        if (!target) return;
        grid.insertBefore(card, event.key === 'ArrowLeft' ? target : target.nextSibling);
        card.querySelector('.dream-photo-open').focus();
        save(orderBefore);
    });
}
