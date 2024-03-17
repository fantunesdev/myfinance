

export function setMontlyReport(transactions) {
    const revenuesByMont = {},
        expensesByMonth = {},
        investimentsByMonth = {};

    for (const transaction of transactions) {
        let [yearInt, monthInt, dayInt] = transaction.payment_date.split('-').map(Number);
        const date = new Date(yearInt, monthInt -1, dayInt)
        const month = date.getMonth()
        const monthInFull = handleMonth(month);
        const category = getCategory(transaction.category);
        
        if (transaction.type == 'entrada' && transaction.home_screen) {
            if (!revenuesByMont[monthInFull]) {
                revenuesByMont[monthInFull] = 0
            }
            revenuesByMont[monthInFull] += transaction.value;
        } else {
            if (transaction.category != 5 && !category.ignore) {
                if (!expensesByMonth[monthInFull]) {
                    expensesByMonth[monthInFull] = 0
                }
                expensesByMonth[monthInFull] += transaction.value;
            } else {
                if (!investimentsByMonth[monthInFull]) {
                    investimentsByMonth[monthInFull] = 0
                }
                investimentsByMonth[monthInFull] += transaction.value;
            }
        }

    }

    return {
        revenues: revenuesByMont, 
        expenses: expensesByMonth, 
        investments: investimentsByMonth,
    }
}

export function setMonthDataset(report) {
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

function handleMonth(month) {
    switch (month) {
        case 0:
            return 'january';
        case 1:
            return 'february';
        case 2:
            return 'march';
        case 3:
            return 'april';
        case 4:
            return 'may';
        case 5:
            return 'june';
        case 6:
            return 'july';
        case 7:
            return 'august';
        case 8:
            return 'september';
        case 9:
            return 'october';
        case 10:
            return 'november';
        case 11:
            return 'december';
    }
}

function getCategory(categoryId) {
    const categories = JSON.parse(sessionStorage.getItem('categories'));    
    
    for (const category of categories) {
        if (category.id == categoryId) {
            return category;
        }
    }
}