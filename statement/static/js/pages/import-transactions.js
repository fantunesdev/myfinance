import { divs, selects } from '../layout/elements/transaction-form-elements.js';
import * as services from '../data/services.js';
// import * as tables from '../layout/elements/tables.js';

const fileInput = document.querySelector('#id_file'),
    importBtn = document.querySelector('#import-btn'),
    boxTransactions = document.querySelector('#box-transactions'),
    divImportTransactions = document.querySelector('#div-import-transactions'),
    transactionRows = document.querySelector('#transaction-rows'),
    checkboxCheckAll = document.querySelector('#checkall');

selects.paymentMethod.value = 2;
divs.card.classList.add('toggled');

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

async function sendFile() {
    const csrf = document.getElementsByName('csrfmiddlewaretoken')[0].value;
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
        const transaction = await services.importTransactions(formData, csrf),
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

async function renderBox() {
    const transactions = JSON.parse(sessionStorage.getItem('imported-transactions')),
        accounts = await services.getResource('accounts'),
        cards = await services.getResource('cards'),
        subcategories = await services.getResource('subcategories');

    for (let account of accounts) {
        if (transactions[0].account == account.id) {
            let bank = await services.getSpecificResource('banks', transactions[0].account);
            var accountDescription = bank.description;
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
                const categories = JSON.parse(sessionStorage.getItem('categories'));
                for (let category of categories) {
                    if (category.id == transaction[keys[i]]) {
                        newCell.textContent = category.description;
                    }
                }
            } else if (keys[i] == 'account') {
                newCell.textContent = accountDescription;
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


importBtn.addEventListener('click', () => sendFile());

selects.paymentMethod.addEventListener('change', () => selectPaymentMethod());

checkboxCheckAll.addEventListener('change', function() {
    for (const row of transactionRows.children) {
        row.children[0].children[0].checked = this.checked;
    }
});


