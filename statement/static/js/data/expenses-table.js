export const columnTitles = ['Data', 'Banco/Cartão', 'Categoria', 'Sub-Categoria', 'Descrição', 'Valor', 'Ações'];


export function orderExpensesBySubcategory(transactions, categoryId, expenses) {
    let newTransactions = [];
    for (let i = 0; i < expenses.length; i++) {
        expenses[i].order = i;
    };

    for (let transaction of transactions) {
        if (transaction.category == categoryId) {
            for (let expense of expenses) {
                if (transaction.subcategory == expense.id) {
                    transaction.order = expense.order;
                }
            }
            newTransactions.push(transaction);
        };
    };

    return newTransactions.sort((a, b) => a.order < b.order ? -1 : a.order > b.order ? 1 : 0);
};


export function setData(transaction, subcategories, category, accounts, cards) {
    let data = [],
        account,
        card;

    data.push(transaction.release_date.split('-').reverse().join('/'));
    for (card of cards) {
        if (transaction.card == card.id) {
            data.push(card.icon);
        };
    };
    for (account of accounts) {
        if (transaction.account == account.id) {
            data.push('');
        }
    }
    data.push(category.description);
    for (let subcategory of subcategories) {
        if (transaction.subcategory == subcategory.id) {
            data.push(`${subcategory.name}`);
        }
    }
    data.push(transaction.description);
    data.push(transaction.value.toLocaleString('pt-br',{style: 'currency', currency: transaction.currency}));
    return data;
};


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