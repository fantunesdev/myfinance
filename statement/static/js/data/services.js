/**
 * Consulta na API os lançamentos do mês/ano desejado.
 * @param {string} year - O ano da pesquisa.
 * @param {string} month - O mês da pesquisa.
 * @returns Uma lista de obsjetos literais contendo todos os lançamentos do mês/ano.
 */
export async function getTransactionsByYearAndMonth(year, month) {
    const path = window.location.pathname;
    let accountId,
        cardId,
        url;
        
        if (path.includes('contas')) {
            accountId = path.split('/')[3];
            url = `/api/transactions/accounts/${accountId}/year/${year}/month/${month}/`;
        } else if (path.includes('cartoes')) {
        cardId = path.split('/')[3];
        url = `/api/transactions/card/${cardId}/year/${year}/month/${month}/`;
    } else {
        url = `/api/transactions/year/${year}/month/${month}/`;
    }

    const response = await fetch(url),
        data = await response.json(),
        sessionStorageData = JSON.stringify(data);

    sessionStorage.setItem('transactions', sessionStorageData);
    return data;
}


/**
 * Consulta na API um recurso específico. Geralmente as instâncias de um modelo.
 * @param {string} model - O modelo do recurso. Ex: Categorias, Subcategorias, Bancos, etc.
 * @returns - Uma lista de objetos literais contendo todas as instância do modelo com todas as suas informações específicas.
 */
export async function getResource(model) {
    const url = `/api/${model}/`,
        response = await fetch(url),
        data = await response.json(),
        sessionStorageData = JSON.stringify(data);

    sessionStorage.setItem(`${model}`, sessionStorageData);
    return data;
}


/**
 * Consulta na API uma instância específica do modelo com base no ID.
 * @param {string} model - O nome do modelo.
 * @param {string} id - O ID da instância.
 * @returns - Um objeto literal com todas as informações da instância.
 */
export async function getSpecificResource(model, id) {
    const url = `/api/${model}/${id}/`,
        response = await fetch(url),
        data = await response.json(),
        sessionStorageData = JSON.stringify(data);

    // sessionStorage.setItem(`${model}-${id}`, sessionStorageData);
    return data;
}


/**
 * Consulta na API uma instância específica de um modelo relacionado a outro modelo com base no ID. Por exemplo, a subcategoria de uma categoria.
 * @param {string} model - O nome do modelo.
 * @param {string} related - O nome do modelo relacionado ao primeiro modelo.
 * @param {string} id - O ID da instância.
 * @returns - Um objeto literal com todas as informações da instância.
 */
export async function getRelatedResource(model, related, id) {
    const url = `/api/${model}/${id}/${related}`,
    response = await fetch(url);
    
    return await response.json();
}


/**
 * Faz upload do arquivo dos lançamentos, o backend lê e retorna um JSON com os dados para renderização.
 * 
 * @param {array} formData - um objeto que contém os dados do formulário
 * @param {string} csrf - O CSRF Token
 * @returns - Um JSON com todos os lançamentos do arquivo de carga.
 */
export async function importTransactions(formData, csrf) {
    const url = `/api/transactions/import/`,
        requestOptions = {
        method: "POST",
        headers: {
            'Accept': 'application/json',
            "X-CSRFToken": csrf
        },
        body: formData,
        };

    try {
        const response = await fetch(url, requestOptions),
            transactions = await response.json(),
            sessionStorageData = JSON.stringify(transactions);
        sessionStorage.setItem('imported-transactions', sessionStorageData);
        return transactions;
    } catch (error) {
        return error;
    }
}

/**
 * Obtém o CSRF Token da aplicação Django através dos cookies do navegador
 * 
 * @param {string} name - Nome do cookie: csrftoken
 * @returns {string} - CSRF Token
 */
export function getCsrfToken(name) {
    let cookieValue = null;
    if (document.cookie && dockment.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.lenght; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.lenght + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
            return cookieValue;
        }
    }
}