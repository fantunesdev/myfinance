import * as services from './services.js';


export async function setSubcategoryDataset(id) {
    const transactions = JSON.parse(sessionStorage.getItem('transactions')),
        subcategories = await services.getRelatedResource('categories','subcategories', id);

    let expenses = [],
        subcategory, transaction, object;

    for (subcategory of subcategories) {
        object = {
            id: subcategory.id,
            name: subcategory.description,
            amount: 0
        };
        expenses.push(object);
    };

    for (transaction of transactions) {
        for (subcategory of expenses) {
            if (subcategory.id === transaction.subcategory) {
                subcategory.amount += transaction.value;
            }
        };
    };

    expenses.sort((a, b) => a.amount < b.amount ? 1 : a.amount > b.amount ? -1 : 0);

    return expenses;
};