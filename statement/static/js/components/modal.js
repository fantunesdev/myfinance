import * as services from '../data/services.js';

document.addEventListener('DOMContentLoaded', function () {
    window.showModal = openModal;

    const infos = [
        {
            id: 'subcategory-train-btn',
            label: 'Treinar',
            title: 'Risco de perda de dados!',
            message: 'Ao treinar o modelo, todos os dados de treinamento anteriormente aprendidos serão esquecidos.' +
                     'O modelo será treinado novamente com base em seus dados atuais.<br><br>' +
                     'Tem certeza que deseja continuar?',
            route: 'transaction-classifier/train',
            method: 'POST'
        },
        {
            id: 'subcategory-feedback-btn',
            label: 'Dar Feedback',
            title: 'Preditor de descrição',
            message: 'Você está enviando o feedback manualmente para o modelo. ' +
                     'Se os dados já forem enviados antes, nada novo será feito.<br><br>' +
                     'Tem certeza que deseja continuar?',
            route: 'transaction-classifier/feedback',
            method: 'POST'
        },
        {
            id: 'description-feedback-btn',
            label: 'Dar Feedback',
            title: 'Preditor de descrição',
            message: 'Você está enviando o feedback manualmente para o modelo. ' +
                     'Se os dados já forem enviados antes, nada novo será feito.<br><br>' +
                     'Tem certeza que deseja continuar?',
            route: 'transaction-classifier/description/feedback',
            method: 'POST'
        },
    ]

    infos.forEach((info) => {
        modalHandler(info);
    })
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

function modalHandler(info) {
    const button = document.getElementById(info.id);
    button.addEventListener('click', function () {
        window.showModal(info.title, info.message, async function () {
            hideModal();
            
            button.innerHTML =
                'Treinando <i class="fa-solid fa-rotate-left rotate-icon"></i>';
            
            try {
                const response = await services.sendRequisition(info.route, info.method);

                if (response && response.message) {
                    window.showModal('Sucesso!', response.message);
                } else if (response && response.error) {
                    window.showModal('Erro', response.error);
                } else {
                    window.showModal('Erro!', 'Resposta desconhecida do servidor.');
                }
            } catch (error) {
                console.error('Error:', error);
                window.showModal('Erro!', 'Erro ao processar a requisição.');
            } finally {
                button.innerHTML = info.label;
            }
        });
    });
}
