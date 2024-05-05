import * as categoryData from '../data/categories-report.js';
import * as subcategoryData from '../data/subcategory-expenses.js';
import * as dataTable from '../data/expenses-table.js';
import * as graphics from '../layout/elements/graphics.js';
import * as tables from '../layout/elements/tables.js';
import * as services from '../data/services.js';
import { originalTable, statementBox } from '../layout/elements/get-transactions-elements.js';
import * as transactionObjectConversor from '../data/transactions-object-conversor.js';
import * as objectToCSVConversor from '../data/objectToCsvConversor.js';
import * as general from '../data/general.js';

const yearNavigation = document.getElementById('id_year'),
    monthNavigation = document.getElementById('id_month'),
    transactionDownloadButton = document.getElementById('download-transactions-button');
    
/**
 * Busca todas as informações para desenhar os gráficos de barras e de donuts.
 * @returns - Um gráfico de barras.
 */
async function draw() {
    // busca todas as informações, classifica e faz os cálculos para montar os gráficos.
    const [year, month] = await categoryData.getMonthYear(),
        transactions = await services.getTransactionsByYearAndMonth(year, month),
        categories = await services.getResource('categories'),
        report = categoryData.setCategoriesReport(transactions, categories),
        revenue = categoryData.setCategoriesDataset(report.revenue, true),
        expenses = categoryData.setCategoriesDataset(report.expenses),
        amount = categoryData.setAmountDataset(report.amount);

    const barChart = graphics.drawBarChart(expenses, 'Despesas');
    graphics.drawDoughnutChart(revenue, 'revenue', 'Receitas');
    graphics.drawDoughnutChart(amount, 'amount', 'Receitas/Despesas');    

    return barChart;
}


/**
 * Atualiza o gráfico de barras conforme a categoria selecionada.
 * @param {Object} barChart - A instância original do gráfico de barras
 */
export async function updateBarChart(barChart) {
    const transactions = JSON.parse(sessionStorage.getItem('transactions')),
        categories = JSON.parse(sessionStorage.getItem('categories'));

    let barLabelClicked = sessionStorage.getItem('bar_label_clicked')

    if (barLabelClicked) {
        for (let category of categories) {
            if (category.description == barLabelClicked) {
                var expenses = await subcategoryData.setSubcategoryDataset(category.id);
            }
        }
    } else {
        const categories = JSON.parse(sessionStorage.getItem('categories')),
            report = categoryData.setCategoriesReport(transactions, categories);
        var expenses = report.expenses;
    }
    
    const dataset = categoryData.setCategoriesDataset(expenses);
    graphics.updateChart(barChart, dataset);
    
    updateTable(transactions, expenses)
}


/**
 * Atualiza a tabela com os registros de 
 * @param {Array} transactions - Uma lista de lançamentos.
 * @param {Array} expenses - Uma lista de subcategorias do tipo despesas.
*/
async function updateTable(transactions, expenses) {
    let subcategoryTable = document.getElementById('subcategory-table'),
        barLabelClicked = sessionStorage.getItem('bar_label_clicked');

        
        if (subcategoryTable) {
            subcategoryTable.parentNode.removeChild(subcategoryTable);
        }
        
    if (barLabelClicked) {
        let categories = JSON.parse(sessionStorage.getItem('categories')),
            selectedCategory,
            accounts = JSON.parse(sessionStorage.getItem('accounts')),
            cards = JSON.parse(sessionStorage.getItem('cards')),
            banks = JSON.parse(sessionStorage.getItem('banks'));

        for (let category of categories) {
            if (category.description == barLabelClicked) {
                selectedCategory = category;
            }
        }
        
        if (!accounts) {
            accounts = await services.getResource('accounts'),
            cards = await services.getResource('cards'),
            banks = await services.getResource('banks');
        }
        
        for (let category of categories) {
            if (category.id == selectedCategory.id) {
                const transactionAttrs = {
                        accounts: accounts,
                        cards: cards,
                        category: category,
                        subcategories: expenses,
                        banks: banks
                    }

                originalTable.classList.add('hide');
                let filteredTransactions = dataTable.orderExpensesBySubcategory(transactions, selectedCategory.id, expenses);
                
                tables.renderTable(statementBox, filteredTransactions, transactionAttrs);
            }
            sessionStorage.removeItem('bar_label_clicked');
        }
    } else {
        originalTable.classList.remove('hide');
    }
}

/**
 * Redireciona a a página para a url selecionada pelo options de navegação mês e ano.
 */
function yearMonthRouter() {
    let actualPath = window.location.pathname,
        splitedPath = actualPath.split('/'),
        url,
        card,
        account;

    if (actualPath.includes('conta')) {
        account = splitedPath[3];
        url = `/relatorio_financeiro/contas/${account}/extrato/${yearNavigation.value}/${monthNavigation.value.padStart(2, '0')}/`;
    } else if (actualPath.includes('fatura')) {
        card = splitedPath[3];
        url = `/relatorio_financeiro/cartoes/${card}/fatura/${yearNavigation.value}/${monthNavigation.value.padStart(2, '0')}/`;
    } else {
        url = `/relatorio_financeiro/${yearNavigation.value}/${monthNavigation.value.padStart(2, '0')}/`;
    }

    window.location.href = url;
}

async function downloadTransactions() {
    const transactions = JSON.parse(sessionStorage.getItem('transactions')),
        deletedProperties = [
            'annual', 'currency', 'effected', 'fixed', 'home_screen', 'id', 'installment', 'installments_number', 'observation',
            'paid', 'remember', 'user'
        ],
        handledTransactions = [];

    for (let transaction of transactions) {
        transaction = await transactionObjectConversor.setTransaction(transaction);

        if (transaction.account) {
            transaction.account = transaction.account.bank.description;
        } else {
            transaction.account = '';
        }

        if (transaction.card) {
            transaction.card = transaction.card.description;
        } else {
            transaction.card = '';
        }

        transaction.category = transaction.category.description;
        transaction.subcategory = transaction.subcategory.description;
        transaction.payment_date = convertDbDateForDayMonthYearDate(transaction.payment_date);
        transaction.release_date = convertDbDateForDayMonthYearDate(transaction.release_date);
        transaction.value = general.handleCurrency(transaction.value);
        console.log(transaction.value)

        for (let property of deletedProperties) {
            delete transaction[property];
        }

        handledTransactions.push(transaction);
    }

    await objectToCSVConversor.convertTransactions(handledTransactions);
}

function convertDbDateForDayMonthYearDate(date) {
    const [year, month, day] = date.split('-');
    return `${day}/${month}/${year}`;
}
    
const resetDashboardButton = document.querySelector('#reset-dashboard-button');
resetDashboardButton.addEventListener('click', () => {
    updateBarChart(barChart);
    sessionStorage.setItem('bar_chart_level', 'categories');
});

let barChart = await draw();
sessionStorage.setItem('bar_chart_level', 'categories');


// Redireciona para a página do ano selecionado.
yearNavigation.addEventListener('change', () => {
    yearMonthRouter();
});

// Redireciona para a página do mês selecionado.
monthNavigation.addEventListener('change', () => {
    yearMonthRouter();
});

// Botão que faz o download da tabela
transactionDownloadButton.addEventListener('click', () => {
    downloadTransactions();
});