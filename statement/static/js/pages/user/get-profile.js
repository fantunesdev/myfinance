import * as services from '../../data/services.js';

function modalHandler(info) {
    const button = document.getElementById(info.id);
    button.addEventListener('click', function () {
        window.showModal(info.title, info.message, async function () {
            window.hideModal();
            
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
});