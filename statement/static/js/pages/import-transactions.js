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
    };
};

/**
 * Envia o arquivo para o servidor, grava o retorno na localStorage e mostra mensagens de erro do backend.
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
        const transaction = await services.importTransactions(formData),
            importError = document.querySelector('#import-error');
        if (transaction.errors) {
            importError.classList.remove('toggled');
            importError.textContent = transaction.errors;
        } else {
            importError.classList.add('toggled');
            renderBox()
        }
    }
}



/**
 * renderiza as linhas da tabela.
 */
async function renderBox() {
    const transactions = JSON.parse(sessionStorage.getItem('imported-transactions')),
        accounts = await services.getResource('accounts'),
        cards = await services.getResource('cards'),
        subcategories = await services.getResource('subcategories');

    for (let account of accounts) {
        if (transactions[0].account == account.id) {
            var bank = await services.getSpecificResource('banks', transactions[0].account);
        }
    }

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

        let keys = Object.keys(transaction);

        for (let i = 1; i < keys.length; i++) {
            let newCell = newRow.insertCell();
            if (keys[i] == 'category') {
                const categories = await services.getResource('categories');
                for (let category of categories) {
                    if (category.id == transaction[keys[i]]) {
                        newCell.textContent = category.description;
                    }
                }
            } else if (keys[i] == 'account') {
                newCell.textContent = bank.description;
            } else if (keys[i] == 'subcategory') {
                for (let subcategory of subcategories) {
                    if (subcategory.id == transaction[keys[i]]) {
                        newCell.textContent = subcategory.description;
                    }
                }
            }
            else {
                newCell.textContent = transaction[keys[i]];
            }
        }

        transactionRows.appendChild(newRow);
    }
}


/**
 * Envia as transações selecionadas para serem cadastradas no backend.
 */
async function importTransactions() {
    let transacionsIds = [];
    for (let row of transactionRows.children) {
        if (row.firstChild.firstChild.checked) {
            transacionsIds.push(parseInt(row.firstChild.firstChild.id));
        }
    }
    const transactions = JSON.parse(sessionStorage.getItem('imported-transactions')),
        accountSelect = document.querySelector('#id_account'),
        account = await services.getSpecificResource('accounts', accountSelect.value);

    for (let transaction of transactions) {
        if (transacionsIds.includes(transaction.id)) {
            let newTransaction = {
                'release_date': transaction.date,
                'payment_date': transaction.date,
                'account': transaction.account,
                'card': transaction.card ? transaction.card : null,
                'category': transaction.category,
                'subcategory': transaction.subcategory,
                'description': transaction.description,
                'value': transaction.value.replace('.', '').replace(',', '.'),
                'installments_number': transaction.installments_number,
                'paid': transaction.paid,
                'fixed': transaction.fixed,
                'annual': transaction.annual,
                'currency': transaction.currency,
                'observation': transaction.observation,
                'remember': transaction.remember,
                'type': transaction.type,
                'effected': transaction.effected,
                'home_screen': account.home_screen,
                'user': transaction.user,
                'installment': transaction.installment
            }
            let importedTransaciton = await services.createResource('transactions', JSON.stringify(newTransaction));
        }
    }
    window.location.href = '/relatorio_financeiro/mes_atual/';
}


importBtn.addEventListener('click', () => sendFile());

selects.paymentMethod.addEventListener('change', () => selectPaymentMethod());

checkboxCheckAll.addEventListener('change', function() {
    for (const row of transactionRows.children) {
        row.children[0].children[0].checked = this.checked;
    }
});

sendTransactionsBtn.addEventListener('click', () => {
    importTransactions();
});
