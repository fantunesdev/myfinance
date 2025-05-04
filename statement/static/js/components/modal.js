document.addEventListener('DOMContentLoaded', function () {
    window.showModal = openModal;
    window.hideModal = hideModal;
});

function openModal(title, body, onConfirm = null) {
    const modal = document.getElementById('modal');
    const modalContent = modal.querySelector('.modal-content');
    const closeModalBtn = document.getElementById('close-modal');
    const cancelBtn = document.getElementById('cancel-modal');
    const confirmBtn = document.getElementById('confirm-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalBody = document.getElementById('modal-body');
    const modalFooter = document.getElementById('modal-footer');

    modalTitle.textContent = title;
    modalBody.innerHTML = body;

    // Se for só mensagem, esconde os botões
    if (onConfirm === null) {
        modalFooter.style.display = 'none';
    } else {
        modalFooter.style.display = 'flex';

        // Remove eventos antigos
        const newConfirmBtn = confirmBtn.cloneNode(true);
        confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);

        newConfirmBtn.addEventListener('click', async function () {
            await onConfirm();
        });

        cancelBtn.addEventListener('click', hideModal);
        closeModalBtn.addEventListener('click', hideModal);
    }

    modal.style.display = 'flex';
    modalContent.classList.remove('fade-out');
    modalContent.classList.add('fade-in');
}

function hideModal() {
    const modal = document.getElementById('modal');
    const modalContent = modal.querySelector('.modal-content');

    modalContent.classList.remove('fade-in');
    modalContent.classList.add('fade-out');

    function handleAnimationEnd() {
        modal.style.display = 'none';
        modalContent.classList.remove('fade-out');
        modalContent.removeEventListener('animationend', handleAnimationEnd);
        modal.removeEventListener('click', clickOutsideHandler);
    }

    function clickOutsideHandler(e) {
        if (e.target === modal) {
            hideModal();
        }
    }

    modal.addEventListener('click', clickOutsideHandler);
    modalContent.addEventListener('animationend', handleAnimationEnd);
}
