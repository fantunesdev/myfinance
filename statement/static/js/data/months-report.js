

export function setMontlyReport(transactions) {
    const revenuesByMont = {},
        expensesByMonth = {},
        investimentsByMonth = {};

    for (let index = 0; index < 12; index++) {
        const monthInFull = handleMonth(index);
        revenuesByMont[monthInFull] = 0;
        expensesByMonth[monthInFull] = 0;
        investimentsByMonth[monthInFull] = 0;
    }

    for (const transaction of transactions) {
        let [yearInt, monthInt, dayInt] = transaction.payment_date.split('-').map(Number);
        const date = new Date(yearInt, monthInt -1, dayInt)
        const month = date.getMonth()
        const monthInFull = handleMonth(month);
        const category = getCategory(transaction.category);
        
        if (transaction.type == 'entrada' && transaction.home_screen) {
            revenuesByMont[monthInFull] += transaction.value;
        } else {
            if (transaction.category != 5 && !category.ignore) {
                expensesByMonth[monthInFull] += transaction.value;
            } else {
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
        names.push(translateMonth(key));
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

function translateMonth(month) {
    switch (month) {
        case 'january':
            return 'Janeiro';
        case 'february':
            return 'Fevereiro';
        case 'march':
            return 'Março';
        case 'april':
            return 'Abril';
        case 'may':
            return 'Maio';
        case 'june':
            return 'Junho';
        case 'july':
            return 'Julho';
        case 'august':
            return 'Agosto';
        case 'september':
            return 'Setembro';
        case 'october':
            return 'Outubro';
        case 'november':
            return 'Novembro';
        case 'december':
            return 'Dezembro';
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