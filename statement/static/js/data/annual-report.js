export function setAnnualReport(transactions) {
    const revenues = {};
    const expenses = {};
    const investments = {};
    const firstYear = transactions[0].payment_date.split('-')[0]
    const lastYear = transactions[transactions.length -1].payment_date.split('-')[0]

    for (let index = firstYear; index <= lastYear; index++) {
        revenues[index] = 0;
        expenses[index] = 0;
        investments[index] = 0;
    }

    for (const transaction of transactions) {
        const year = transaction.payment_date.split('-')[0];
        const category = getCategory(transaction.category);

        if (transaction.type == 'entrada') {
            revenues[year] += transaction.value;
        } else {
            if (transaction.category != 5 && !category.ignore) {
                expenses[year] += transaction.value;
            } else if (transaction.category == 5) {
                investments[year] += transaction.value
            }
        }
    }

    return {
        revenues: revenues,
        expenses: expenses,
        investments: investments,
    }
}

export function setAnnualDataset(report) {
    let names = [],
        values = [],
        colors = [],
        key;

    for (key in report) {
        names.push(key);
        values.push(report[key]);
        colors.push(`rgba(139, 0, 0, 1)`);
    }
    return {names, values, colors}
}

function getCategory(categoryId) {
    const categories = JSON.parse(sessionStorage.getItem('categories'));    
    
    for (const category of categories) {
        if (category.id == categoryId) {
            return category;
        }
    }
}