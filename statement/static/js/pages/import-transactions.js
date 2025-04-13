import { divs, selects } from '../layout/elements/transaction-form-elements.js';
import * as services from '../data/services.js';
// import * as tables from '../layout/elements/tables.js';

const fileInput = document.querySelector('#id_file'),
    importBtn = document.querySelector('#import-btn'),
    boxTransactions = document.querySelector('#box-transactions'),
    divImportTransactions = document.querySelector('#div-import-transactions'),
    transactionRows = document.querySelector('#transaction-rows'),
    checkboxCheckAll = document.querySelector('#checkall'),
    sendTransactionsBtn = document.querySelector('#send-transactions-btn');

selects.paymentMethod.value = 2;
divs.card.classList.add('toggled');

/**
 * Configura os selects relacionados ao meio de pagamento.
 */
export function selectPaymentMethod() {
    const paymentMethod = selects.paymentMethod.value;
    if (paymentMethod == 1) {
        divs.account.classList.add('toggled');
        divs.card.classList.remove('toggled');
        selects.card.required = true;
        selects.account.required = false;
        selects.account.selectedIndex = 0;
    } else {
        divs.card.classList.add('toggled');
        divs.account.classList.remove('toggled');
        selects.account.required = true;
        selects.card.required = false;
        selects.card.selectedIndex = 0;
    }
}

/**
 * Verifica se o arquivo foi enviado e se o meio de pagamento foi selecionado.
 * Se tudo estiver correto, envia o arquivo para o backend.
 */
async function sendFile() {
    const formData = new FormData();

    formData.append('file', fileInput.files[0]);
    formData.append('account', isNaN(parseInt(selects.account.value)) ? '' : parseInt(selects.account.value));
    formData.append('card', isNaN(parseInt(selects.card.value)) ? '' : parseInt(selects.card.value));


    if (!fileInput.files[0]) {
        alert('Selecione um arquivo para continuar.');
        return;
    }
    if (selects.paymentMethod.value == 1 && !selects.card.value) {
        alert('Selecione um cartão para continuar.');
    } else if (selects.paymentMethod.value == 2 && !selects.account.value) {
        alert('Selecione uma conta para continuar.');
    } else {
        const transactions = await services.importTransactions(formData);
        window.myFinance = window.myFinance || {};
        window.myFinance.importedTransactions = transactions;
        const importError = document.querySelector('#import-error');
        if (transactions.errors) {
            importError.classList.remove('toggled');
            importError.textContent = transactions.errors;
        } else {
            importError.classList.add('toggled');
            renderBox(transactions);
        }
    }
}



/**
 * Renderiza a tabela de transações importadas.
 * Cada linha da tabela representa uma transação importada.
 * As colunas da tabela são: data, descrição, valor, categoria, subcategoria e conta/cartão.
 * 
 * @todo - Dividir a função em funções menores pra facilitar a leitura e manutenção. 
 * @param {array} transactions - Um array de transações importadas do arquivo da instituição financeira.
 */
async function renderBox(transactions) {
    const categories = await services.getResource('categories');

    boxTransactions.classList.remove('toggled');
    while (transactionRows.firstChild) {
        transactionRows.removeChild(transactionRows.firstChild);
    }

    for (let transaction of transactions) {
        let newRow = document.createElement('tr');

        let checkboxCell = newRow.insertCell();
        let checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.id = transaction.id;
        checkboxCell.appendChild(checkbox);

        // Adiciona evento para alterar a opacidade da linha para melhorar a legibilidade
        checkbox.addEventListener('change', function () {
            if (this.checked) {
                newRow.classList.remove('row-disabled');
            } else {
                newRow.classList.add('row-disabled');
            }
        });

        // Define a classe opaca inicialmente se o checkbox não estiver marcado
        if (!checkbox.checked) {
            newRow.classList.add('row-disabled');
        }

        let keys = Object.keys(transaction);

        for (let i = 1; i < keys.length; i++) {
            let key = keys[i];

            if (['date', 'category', 'subcategory', 'description', 'value'].includes(key)) {
                let newCell = newRow.insertCell();

                if (key === 'date') {
                    let input = document.createElement('input');
                    input.id = `${key}_${transaction.id}`;
                    input.type = 'date';
                    input.value = transaction.date;
                    input.classList.add('form-control');
                    newCell.appendChild(input);
                }

                if (key === 'category') {
                    let select = document.createElement('select');
                    select.id = `${key}_${transaction.id}`;
                    select.classList.add('form-control');

                    categories.forEach(category => {
                        let option = document.createElement('option');
                        option.value = category.id;
                        option.textContent = category.description;
                        if (category.id === transaction.category) {
                            option.selected = true;
                        }
                        select.appendChild(option);
                    });

                    // Adiciona o evento onchange para atualizar as subcategorias
                    select.addEventListener('change', async function () {
                        const subcategorySelect = newCell.nextSibling.querySelector('select');
                        const subcategories = await services.getChildrenResource('categories', 'subcategories', select.value);

                        // Limpa as opções existentes no select de subcategorias
                        subcategorySelect.innerHTML = '';

                        // Adiciona as novas opções de subcategorias
                        subcategories.forEach(subcategory => {
                            let option = document.createElement('option');
                            option.value = subcategory.id;
                            option.textContent = subcategory.description;
                            subcategorySelect.appendChild(option);
                        });
                    });

                    newCell.appendChild(select);
                }

                if (key === 'subcategory') {
                    let select = document.createElement('select');
                    select.id = `${key}_${transaction.id}`;
                    select.classList.add('form-control');

                    const subcategories = await services.getChildrenResource('categories', 'subcategories', transaction.category);
                    subcategories.forEach(subcategory => {
                        let option = document.createElement('option');
                        option.value = subcategory.id;
                        option.textContent = subcategory.description;
                        if (subcategory.id === transaction.subcategory) {
                            option.selected = true;
                        }
                        select.appendChild(option);
                    });

                    newCell.appendChild(select);
                }

                if (key === 'description') {
                    let input = document.createElement('input');
                    input.id = `${key}_${transaction.id}`;
                    input.type = 'text';
                    input.value = transaction.description;
                    input.classList.add('form-control');
                    newCell.appendChild(input);
                }

                if (key === 'value') {
                    newCell.textContent = transaction.value;
                }
            }
        }

        transactionRows.appendChild(newRow);
    }
}


/**
 * Envia as transações selecionadas para o backend.
 * Faz a validação dos dados e cadastra as transações no banco de dados.
 * 
 * @todo - A função está funcional novamente, mas ainda precisa de alguns ajustes.
 * @todo - 1 - Pegar os valores dos inputs de data, categoria, subcategoria e descrição.
 * @todo - 2 - O valor está ficando sem ponto flutuante. Ex R: 1000,00 está ficando 100000.
 * @todo - 3 - É necessário implementar a lógica para verificar se houve alteração entre o valor original (transaction) e o novo valor (formulário).
 * @todo - 4 - Criar uma nova função para cadastrar o CategorizationFeedback.
 * @todo - 5 - Dividir a função em funções menores pra facilitar a leitura e manutenção.
 * 
 * @param {array} transactions - Um array de transações importadas do arquivo da instituição financeira.
 *
 * @returns - Redireciona para a tela de relatório financeiro.
 */
async function importTransactions(transactions) {
    let transactionsIds = [];

    for (let row of transactionRows.children) {
        if (row.firstChild.firstChild.checked) {
            transactionsIds.push(parseInt(row.firstChild.firstChild.id));
        }
    }

    const paymentMethod = document.querySelector('#id_payment_method');
    const accountSelect = document.querySelector('#id_account');
    const cardSelect = document.querySelector('#id_card');

    let homeScreen;    
        
    if (paymentMethod.value == 2) {
        let account = await services.getSpecificResource('accounts', accountSelect.value);
        homeScreen = account.home_screen;
    } else {
        let card = await services.getSpecificResource('cards', cardSelect.value);
        homeScreen = card.home_screen;
    }

    let errors = 0;

    for (let transaction of transactions) {
        if (transactionsIds.includes(transaction.id)) {
            let newTransaction = {
                'release_date': transaction.date,
                'account': transaction.account ? transaction.account : null,
                'card': transaction.card ? transaction.card : null,
                'category': transaction.category,
                'subcategory': transaction.subcategory,
                'description': transaction.description,
                'value': transaction.value.replace('.', '').replace(',', '.'),
            }
            const importError = document.querySelector('#import-error');
            try {
                let response = await services.createResource('transactions', JSON.stringify(newTransaction));
                importError.classList.add('toggled');
                if (response instanceof Error) {
                    errors += 1;
                    throw new Error(response.message);
                }
            } catch (error) {
                importError.classList.remove('toggled');
                importError.textContent = `${error.message}: ${JSON.stringify(newTransaction)}`;
                break;
            }
        }
    }
    if (errors == 0) {
        window.location.href = '/relatorio_financeiro/mes_atual/';
    }
}


importBtn.addEventListener('click', () => sendFile());

selects.paymentMethod.addEventListener('change', () => selectPaymentMethod());

checkboxCheckAll.addEventListener('change', function() {
    for (const row of transactionRows.children) {
        const checkbox = row.children[0].children[0];
        checkbox.checked = this.checked;

        // Adiciona ou remove a classe 'row-disabled' com base no estado do checkbox
        if (checkbox.checked) {
            row.classList.remove('row-disabled');
        } else {
            row.classList.add('row-disabled');
        }
    }
});

sendTransactionsBtn.addEventListener('click', () => {
    const transactions = window.myFinance.importedTransactions;
    importTransactions(transactions);
});
