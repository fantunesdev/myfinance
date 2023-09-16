import * as services from "./services.js";


export async function getMonthYear() {
    let url = window.location.pathname,
        currentMonth = url.indexOf('mes_atual') >= 0 ? true : false,
        root = url === '/' ? true : false,
        today = new Date(), 
        month, year;

    const nextMonthView = await services.getResource('next_month_view');
    
    if (root || currentMonth) {
        month = today.getDate() < nextMonthView.day && nextMonthView.active ? today.getMonth() + 1 : today.getMonth() + 2;
        year = month <= 12 ? today.getFullYear() : today.getFullYear() + 1;
        month = month === 13 ? 1 : month;
    } else {
        if (url.includes('contas') || url.includes('cartoes')) {
            year = url.split('/')[6];
            month = url.split('/')[7]
        } else {
            year = url.split('/')[2];
            month = url.split('/')[3];
        }
    };

    return [year, month];
};


export async function setCategoriesReport(transactions) {
    let categories = await services.getResource('categories'),
        revenue = [],
        expenses = [],
        amount = {
            revenue: 0, 
            expenses: 0
        },
        category;

    for (category of categories) {
        let object = {
            id: category.id,
            name: category.description,
            amount: 0
        };

        if (category.type === 'entrada') {
            revenue.push(object);
        } else {
            if (!category.ignore) {
                expenses.push(object);
            }
        };
    };

    for (let transaction of transactions) {

        for (category of revenue) {
            if (transaction.category === category.id) {
                category.amount += transaction.value;
            }
        };
        
        for (category of expenses) {
            if (transaction.category === category.id) {
                category.amount += transaction.value;
            }
        };
        
        if (transaction.type === 'entrada') {
            amount.revenue += transaction.value;            
        } else {
            let transactionCategory = await services.getSpecificResource('categories', transaction.category);

            if (!transactionCategory.ignore) {
                amount.expenses += transaction.value;
            }
        }
    };

    expenses.sort((a, b) => a.amount < b.amount ? 1 : a.amount > b.amount ? -1 : 0);
    
    return {revenue, expenses, amount};
};


export function setCategoriesDataset(report, revenue) {
    let names = [],
        values = [],
        colors = [],
        category,
        green = 139;

    for (category of report) {
        names.push(category.name);
        values.push(category.amount);
        if (revenue) {
            colors.push(`rgba(0, ${green}, 0, 1)`);
            green -= 30;
        } else {
            colors.push(`rgba(139, 0, 0, 1)`);
        }
    }
    return {names, values, colors};
};


export function setCategoriesOptions(report) {
    let options = [],
        object;

    for (let i of report) {
        object = {
            id: i.id,
            description: i.name,
            amount: i.amount
        }
        options.push(object)
    };
    return options;
}


export function setAmountDataset(amount) {
    let names = ['Entradas', 'Saídas'],
        values = [amount.revenue, amount.expenses],
        colors = [
            'rgba(0, 150, 0, 1)',
            'rgba(139, 0, 0, 1)'
        ]
    return {names, values, colors};
};