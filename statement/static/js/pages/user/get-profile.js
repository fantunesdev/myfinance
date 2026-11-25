import * as services from '../../data/services.js?v=classifier-jobs-2';
import { startClassifierJob } from './classifier-jobs.js?v=profile-modals-1';

const infos = [
    {
        id: 'subcategory-train-btn',
        label: 'Treinar',
        title: 'Risco de perda de dados!',
        message: 'Ao treinar o modelo, todos os dados de treinamento anteriormente aprendidos serão esquecidos.' +
                 'O modelo será treinado novamente com base em seus dados atuais.\n\n' +
                 'Tem certeza que deseja continuar?',
        route: 'transaction-classifier/subcategory/train',
        method: 'POST'
    },
    {
        id: 'subcategory-feedback-btn',
        label: 'Dar Feedback',
        title: 'Enviar feedback',
        message: 'Você está enviando o feedback manualmente para o modelo. ' +
                 'Se os dados já forem enviados antes, nada novo será feito.\n\n' +
                 'Tem certeza que deseja continuar?',
        route: 'transaction-classifier/subcategory/feedback',
        method: 'POST'
    },
    {
        id: 'description-train-btn',
        label: 'Treinar',
        title: 'Risco de perda de dados!',
        message: 'Ao treinar o modelo, todos os dados de treinamento anteriormente aprendidos serão esquecidos.' +
                 'O modelo será treinado novamente com base em seus dados atuais.\n\n' +
                 'Tem certeza que deseja continuar?',
        route: 'transaction-classifier/description/train',
        method: 'POST'
    },
    {
        id: 'description-feedback-btn',
        label: 'Dar Feedback',
        title: 'Enviar feedback',
        message: 'Você está enviando o feedback manualmente para o modelo. ' +
                 'Se os dados já forem enviados antes, nada novo será feito.\n\n' +
                 'Tem certeza que deseja continuar?',
        route: 'transaction-classifier/description/feedback',
        method: 'POST'
    },
    {
        id: 'delete-feedbacks-btn',
        label: 'Apagar Feedbacks',
        title: 'Risco de perda de dados!',
        message: 'Atenção! Você está prestes a apagar todos os feedbacks gravados! ' +
                 'VOCÊ NÃO PODERÁ MAIS USÁ-LOS PARA TREINAMENTO! ' +
                 'Esta ação não reverterá nenhum treinamento realizado. \n\n' +
                 'Tem certeza que deseja continuar?',
        route: 'transaction-classifier/delete',
        method: 'POST'
    },

]

const boundButtons = new WeakSet();
window.addEventListener?.('profile:updated', () => infos.forEach(modalHandler));

infos.forEach((info) => {
    modalHandler(info);
});

function modalHandler(info) {
    const button = document.getElementById(info.id);
    if (!button || boundButtons.has(button)) return;
    boundButtons.add(button);
    button.addEventListener('click', function () {
        window.showModal(info.title, info.message, async function () {
            window.hideModal();
            
            if (/^transaction-classifier\/(subcategory|description)\/(train|feedback)$/.test(info.route)) {
                await startClassifierJob(info.route);
                return;
            }

            button.innerHTML =
                'Treinando <i class="fa-solid fa-rotate-left rotate-icon"></i>';
            
            try {
                const response = await services.sendRequisition(info.route, info.method);

                if (response instanceof Error) {
                    throw response;
                } else if (response && response.error) {
                    window.myFinanceToast(response.error, 'error');
                } else if (response && response.success === false) {
                    window.myFinanceToast(response.message || 'A operação não foi concluída.', 'error');
                } else if (response && response.message) {
                    window.myFinanceToast(response.message, 'success');
                } else {
                    window.myFinanceToast('Resposta desconhecida do servidor.', 'error');
                }
            } catch (error) {
                console.error('Error:', error);
                window.myFinanceToast('Erro ao processar a requisição.', 'error');
            } finally {
                button.innerHTML = info.label;
            }
        });
    });
}

