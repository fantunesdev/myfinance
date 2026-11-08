import * as chartPolicy from './chart-policy.js';

export const columnTitles = ['Data', 'Banco/Cartão', 'Categoria', 'Sub-Categoria', 'Descrição', 'Valor', 'Ações'];

export function orderExpensesBySubcategory(transactions, categoryId, expenses) {
    let newTransactions = [];
    for (let i = 0; i < expenses.length; i++) {
        expenses[i].order = i;
    }

    for (let transaction of transactions) {
        if (!chartPolicy.showInMonthlyExpenseCategoryBar(transaction)) continue;

        if (transaction.category == categoryId) {
            for (let expense of expenses) {
                if (transaction.subcategory == expense.id) {
                    transaction.order = expense.order;
                }
            }
            newTransactions.push(transaction);
        }
    }

    return newTransactions.sort((a, b) => (a.order < b.order ? -1 : a.order > b.order ? 1 : 0));
}

const resourceId = resource => resource && typeof resource === 'object' ? resource.id : resource;

function resolveResource(resources, reference) {
    const found = (resources || []).find(resource => String(resource.id) === String(resourceId(reference)));
    return { ...found, ...(reference && typeof reference === 'object' ? reference : {}) };
}

export function setData(transaction, transactionAttrs) {
    const cardReference = transaction.card || transaction.card_number?.card;
    const card = resolveResource(transactionAttrs.cards, cardReference);
    const account = resolveResource(transactionAttrs.accounts, transaction.account);
    const bank = resolveResource(transactionAttrs.banks, account.bank);
    const icon = card.icon || bank.icon || '';
    const subcategory = (transactionAttrs.subcategories || []).find(
        item => String(item.id) === String(resourceId(transaction.subcategory))
    );

    return [
        transaction.posted_date.split('-').reverse().join('/'),
        icon,
        transactionAttrs.category.description,
        subcategory?.name || subcategory?.description || '-',
        transaction.description,
        transaction.value.toLocaleString('pt-br', {
            style: 'currency',
            currency: transaction.currency,
        }),
    ];
}

export function setURLs(transaction) {
    let urls = [];

    if (transaction.installment) {
        urls = [
            `/relatorio_financeiro/parcelamento/${transaction.installment}/`,
            `/relatorio_financeiro/parcelamento/editar/${transaction.installment}/`,
            `/relatorio_financeiro/parcelamento/remover/${transaction.installment}/`,
        ];
    } else {
        urls = [
            `/relatorio_financeiro/${transaction.id}/`,
            `/relatorio_financeiro/editar/${transaction.id}/`,
            `/relatorio_financeiro/remover/${transaction.id}`,
        ];
    }
    return urls;
}
