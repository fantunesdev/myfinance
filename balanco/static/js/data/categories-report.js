import * as services from "./services.js";


export function getMonthYear() {
    let url = window.location.pathname,
        currentMonth = url.indexOf('mes_atual') >= 0 ? true : false,
        root = url === '/' ? true : false,
        today = new Date(), 
        month, year;
    
    if (root || currentMonth) {
        month = today.getDate() < 10 ? today.getMonth() + 1 : today.getMonth() + 2;
        year = month <= 12 ? today.getFullYear() : today.getFullYear() + 1;
        month = month === 13 ? 1 : month;
    } else {
        year = url.split('/')[2];
        month = url.split('/')[3];
    };

    return {year, month};
};


export async function setCategoriesReport(year, month) {
    let movements = await services.getMovementsYearMonth(year, month),
        categories = await services.getView('categorias'),
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
            name: category.descricao,
            amount: 0
        }
        if (category.tipo === 'entrada') {
            revenue.push(object);
        } else {
            if (category.id !== 13) {
                expenses.push(object);
            }
        };
    };

    for (let movement of movements) {

        for (category of revenue) {
            if (movement.categoria === category.id) {
                category.amount += movement.valor;
            }
        };
        
        for (category of expenses) {
            if (movement.categoria === category.id) {
                category.amount += movement.valor;
            }
        };
        
        if (movement.tipo === 'entrada') {
            amount.revenue += movement.valor;            
        } else {
            if (movement.categoria !== 13) {
                amount.expenses += movement.valor;
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
        red = 139;

    for (category of report) {
        names.push(category.name);
        values.push(category.amount);
        colors.push(`rgba(${red}, 0, 0, 1)`);
        if (revenue) {
            red += 30;
        }
    }
    return {names, values, colors};
};


export function setAmountDataset(amount) {
    let names = ['Entradas', 'Saídas'],
        values = [amount.revenue, amount.expenses],
        colors = [
            'rgba(0, 150, 0, 1)',
            'rgba(139, 0, 0, 1)'
        ]
    return {names, values, colors};
};