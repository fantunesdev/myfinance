import * as services from "./services.js";


export async function getMonthYear() {
    let path = window.location.pathname,
        currentMonth = path.indexOf('mes_atual') >= 0 ? true : false,
        root = path === '/' ? true : false,
        today = new Date(), 
        month,
        year;

    const nextMonthView = await services.getResource('next_month_view');
    
    if (root || currentMonth) {
        if (path.includes('contas')) {
            month = today.getMonth() + 1;
            year = today.getFullYear();
        } else {
            month = today.getDate() < nextMonthView.day && nextMonthView.active ? today.getMonth() + 1 : today.getMonth() + 2;
            year = month <= 12 ? today.getFullYear() : today.getFullYear() + 1;
            month = month === 13 ? 1 : month;
        }
    } else {
        if (path.includes('contas') || path.includes('cartoes')) {
            year = path.split('/')[5];
            month = path.split('/')[6]
        } else {
            year = path.split('/')[2];
            month = path.split('/')[3];
        }
    };

    const yearMonth = [year, month];

    sessionStorage.setItem('year-month', yearMonth)

    return yearMonth;
};


/**
 * Monta um relatório que classifica os lançamentos em receitas e despesas calculando o montante total de ambas.
 * @param {Array} transactions - Uma lista de instâncias da classe Transactions.
 * @returns {Object} - Um objeto literal contendo a lista classificada de receitas, despesas e o valor da soma total de recitas e despesas.
 */
export async function setCategoriesReport(transactions) {
    // Busca na API todas as categorias.
    let categories = await services.getResource('categories'),
        revenue = [],
        expenses = [],
        amount = {
            revenue: 0, 
            expenses: 0
        },
        category;
    
    // Separa as categorias de receitas e de despesas.
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

    // Classifica os lançamentos como receitas e despesas e calcula o montante total de ambas.
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
            for (let category of categories) {
                if (!category.ignore) {
                    amount.expenses += transaction.value;
                }

            }
        }
    };

    // Ordena as despesas pelo montante. Os maiores gastos aparecem primeiro.
    expenses.sort((a, b) => a.amount < b.amount ? 1 : a.amount > b.amount ? -1 : 0);
    
    return {revenue, expenses, amount};
};


/**
 * Constrói um objeto literal com os dados que serão usados que o ChartJS precisa para montar o gráfico.
 * Obs: Por uma questão de reaproveitamento de código, será necessário passar receitas e despesas separadamente, 
 * assinalando no parâmetro REVENUE se é o dataset de receitas ou não par alterar a cor do gráfico.
 * @param {Object} report - O objeto literal com as receitas, despesas e seus respectivos montantes.
 * @param {boolean} revenue - Um boleano que discrimina se a classificação é por receitas.
 * @returns {Object} - Um objeto literal contendo os nomes das categorias dos lançamentos, o montante e a cor a ser utilizada no gráfico.
 */
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


/**
 * Constrói a base de dados que será utilizada pra renderizar o select com as opções para selecionar as categorias.
 * @param {Array} report - Uma lista de objetos literais. Neste caso, relacionados ao modelo de categorias.
 * @returns {Array}
 */
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

/**
 * Constrói um objeto literal com as informações que serão usadas para montar o DonutChart com o total de receitas e despesas.
 * @param {Object} amount - Um objeto literal com o valor total das receitas e das despesas.
 * @returns - Um objeto literal com os nome, valores e cores a serem utilizados pelo ChartJS.
 */
export function setAmountDataset(amount) {
    let names = ['Entradas', 'Saídas'],
        values = [amount.revenue, amount.expenses],
        colors = [
            'rgba(0, 150, 0, 1)',
            'rgba(139, 0, 0, 1)'
        ]
    return {names, values, colors};
};