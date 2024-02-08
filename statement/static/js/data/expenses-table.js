import * as services from '../data/services.js'

export const columnTitles = ['Data', 'Banco/Cartão', 'Categoria', 'Sub-Categoria', 'Descrição', 'Valor', 'Ações'];


export function orderExpensesBySubcategory(transactions, categoryId, expenses) {
    let newTransactions = [];
    for (let i = 0; i < expenses.length; i++) {
        expenses[i].order = i;
    }

    for (let transaction of transactions) {
        if (transaction.category == categoryId) {
            for (let expense of expenses) {
                if (transaction.subcategory == expense.id) {
                    transaction.order = expense.order;
                }
            }
            newTransactions.push(transaction);
        }
    }

    return newTransactions.sort((a, b) => a.order < b.order ? -1 : a.order > b.order ? 1 : 0);
}


export function setData(transaction, transactionAttrs) {
    let data = [],
        account,
        card,
        bank,
        releaseDateFormated = transaction.release_date.split('-').reverse().join('/');

    
    // Column 1 - Release dates data
    data.push(releaseDateFormated);

    // Column 2 - Cards/Accounts data
    // If cards:
    for (card of transactionAttrs.cards) {
        if (transaction.card == card.id) {
            data.push(card.icon);
        }
    }

    // If accounts:
    for (account of transactionAttrs.accounts) {
        if (transaction.account == account.id) {
            for (bank of transactionAttrs.banks) {
                if (bank.id == account.bank) {
                    data.push(bank.icon);
                }
            }
        }
    }

    // Column 3 - Category data
    data.push(transactionAttrs.category.description);

    // Column 4 - Subcategories data
    for (let subcategory of transactionAttrs.subcategories) {
        if (transaction.subcategory == subcategory.id) {
            data.push(`${subcategory.name}`);
        }
    }

    // Column 5 - Description data
    data.push(transaction.description);

    // Column 6 - Value data
    data.push(transaction.value.toLocaleString('pt-br',{style: 'currency', currency: transaction.currency}));
    
    return data;
}


export function setURLs(transaction) {
    let urls = [];
    
    if (transaction.installment) {
        urls = [
            `/parcelamento/${transaction.installment}/`,
            `/parcelamento/editar/${transaction.installment}`,
            `/parcelamento/remover/${transaction.installment}`
        ]
    } else {
        urls = [
            `/movimentacao/${transaction.id}/`,
            `/movimentacao/editar/${transaction.id}`,
            `/movimentacao/remover/${transaction.id}`
        ]
    }    
    return urls;
}