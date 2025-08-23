import * as services from '../../data/services.js';

const infos = [
    {
        id: 'subcategory-train-btn',
        label: 'Treinar',
        title: 'Risco de perda de dados!',
        message: 'Ao treinar o modelo, todos os dados de treinamento anteriormente aprendidos serão esquecidos.' +
                 'O modelo será treinado novamente com base em seus dados atuais.<br><br>' +
                 'Tem certeza que deseja continuar?',
        route: 'transaction-classifier/subcategory/train',
        method: 'POST'
    },
    {
        id: 'subcategory-feedback-btn',
        label: 'Dar Feedback',
        title: 'Preditor de descrição',
        message: 'Você está enviando o feedback manualmente para o modelo. ' +
                 'Se os dados já forem enviados antes, nada novo será feito.<br><br>' +
                 'Tem certeza que deseja continuar?',
        route: 'transaction-classifier/subcategory/feedback',
        method: 'POST'
    },
    {
        id: 'description-train-btn',
        label: 'Treinar',
        title: 'Risco de perda de dados!',
        message: 'Ao treinar o modelo, todos os dados de treinamento anteriormente aprendidos serão esquecidos.' +
                 'O modelo será treinado novamente com base em seus dados atuais.<br><br>' +
                 'Tem certeza que deseja continuar?',
        route: 'transaction-classifier/description/train',
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
    {
        id: 'delete-feedbacks-btn',
        label: 'Apagar Feedbacks',
        title: 'Risco de perda de dados!',
        message: 'Atenção! Você está prestes a apagar todos os feedbacks gravados! ' +
                 '<b>VOCÊ NÃO PODERÁ MAIS USÁ-LOS PARA TREINAMENTO!</b> ' +
                 'Esta ação não reverterá nenhum treinamento realizado. <br><br>' +
                 'Tem certeza que deseja continuar?',
        route: 'transaction-classifier/delete',
        method: 'POST'
    },
    {
        id: 'next-month-update-btn',
        label: 'Editar',
        title: 'Editar configuração de ver o próximo mês',
        message: 'Decidi que fica mais organizado dividir as configurações em sessões. O Next Month é a primeira, mas futuramente poderão' +
                 ' existir outras. Quando for migrar a implementação do Next Mont pra cá, criar um novo modal de formulário para as configurações.' +
                 'e enviar por PATCH para a API. Vai precisar construir as rotas na API.',
        route: '',
        method: 'PATCH'
    },
]

infos.forEach((info) => {
    modalHandler(info);
});

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

