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
    transactionDownloadButton = document.getElementById('download-transactions-button'),
    monthlyExpensesChartToggle = document.getElementById('monthly-expenses-chart-toggle');

let monthlyExpensesLineChart = null;
let activeExpensesChart = 'bar';
let dashboardTransactions = [];

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

    dashboardTransactions = transactions;

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

    let barLabelClicked = sessionStorage.getItem('bar_label_clicked');

    if (barLabelClicked) {
        for (let category of categories) {
            if (category.description == barLabelClicked) {
                var expenses = await subcategoryData.setSubcategoryDataset(category.id);
            }
        }

        if (!expenses) {
            sessionStorage.removeItem('bar_label_clicked');
            sessionStorage.setItem('bar_chart_level', 'categories');
            const report = categoryData.setCategoriesReport(transactions, categories);
            expenses = report.expenses;
        }
    } else {
        const categories = JSON.parse(sessionStorage.getItem('categories')),
            report = categoryData.setCategoriesReport(transactions, categories);
        var expenses = report.expenses;
    }

    const dataset = categoryData.setCategoriesDataset(expenses);
    graphics.updateChart(barChart, dataset);

    updateTable(transactions, expenses);
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
            (accounts = await services.getResource('accounts')),
                (cards = await services.getResource('cards')),
                (banks = await services.getResource('banks'));
        }

        for (let category of categories) {
            if (category.id == selectedCategory.id) {
                const transactionAttrs = {
                    accounts: accounts,
                    cards: cards,
                    category: category,
                    subcategories: expenses,
                    banks: banks,
                };

                originalTable.classList.add('hide');
                let filteredTransactions = dataTable.orderExpensesBySubcategory(
                    transactions,
                    selectedCategory.id,
                    expenses
                );

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
            'annual',
            'currency',
            'effected',
            'fixed',
            'home_screen',
            'id',
            'installment',
            'installments_number',
            'observation',
            'paid',
            'remember',
            'user',
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
        transaction.posted_date = convertDbDateForDayMonthYearDate(transaction.posted_date);
        transaction.value = general.handleCurrency(transaction.value);

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

function drawMonthlyExpensesLineChart() {
    const canvas = document.getElementById('monthly-expenses-line-chart');
    if (!canvas) return null;

    if (monthlyExpensesLineChart) {
        monthlyExpensesLineChart.destroy();
        monthlyExpensesLineChart = null;
    }

    const categories = JSON.parse(sessionStorage.getItem('categories') || '[]');
    const dataset = setMonthlyExpensesLineDataset(dashboardTransactions, categories);

    monthlyExpensesLineChart = new Chart(canvas.getContext('2d'), {
        type: 'line',
        data: {
            labels: dataset.names,
            datasets: [
                {
                    label: 'Gastos no mês',
                    data: dataset.values,
                    borderColor: 'rgba(139, 0, 0, 1)',
                    backgroundColor: 'rgba(139, 0, 0, 0.15)',
                    fill: true,
                    tension: 0.2,
                },
            ],
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginZero: true,
                },
            },
            plugins: {
                legend: {
                    display: false,
                },
                title: {
                    display: true,
                    text: 'Gastos no mês',
                    font: {
                        size: 18,
                        family: 'Ubuntu',
                    },
                    color: 'rgba(204,204,204,1)',
                },
            },
            animation: {
                duration: 200,
            },
        },
    });

    return monthlyExpensesLineChart;
}

function setMonthlyExpensesLineDataset(transactions, categories) {
    const [year, month] = sessionStorage.getItem('year-month').split(',');
    const selectedYear = Number(year);
    const selectedMonth = Number(month);
    const daysInMonth = new Date(selectedYear, selectedMonth, 0).getDate();
    const dailyExpenses = Array(daysInMonth).fill(0);
    const labels = Array.from({ length: daysInMonth }, (_, index) => String(index + 1).padStart(2, '0'));
    let accumulated = 0;

    for (const transaction of transactions) {
        if (transaction.type === 'entrada') continue;
        if (!isDashboardExpense(transaction, categories)) continue;

        const transactionDay = getMonthlyExpenseDay(transaction, selectedYear, selectedMonth, daysInMonth);
        if (!transactionDay) continue;

        dailyExpenses[transactionDay - 1] += Number(transaction.value || 0);
    }

    const values = dailyExpenses.map(value => {
        accumulated += value;
        return accumulated;
    });

    return { names: labels, values };
}

function getMonthlyExpenseDay(transaction, selectedYear, selectedMonth, daysInMonth) {
    const postedDate = parseDbDateParts(transaction.posted_date);
    const isInstallment = Boolean(
        transaction.installment || transaction.installment_id || Number(transaction.installments_number) > 1
    );
    const isLaterInstallment = isInstallment && Number(transaction.paid || 0) > 1;

    if (isLaterInstallment && postedDate && isBeforeMonth(postedDate, selectedYear, selectedMonth)) {
        return 1;
    }

    if (postedDate) {
        return Math.min(postedDate.day, daysInMonth);
    }

    return null;
}

function parseDbDateParts(date) {
    if (!date) return null;

    if (date.includes('/')) {
        const [day, month, year] = date.split('/').map(Number);
        if (!year || !month || !day) return null;

        return { year, month, day };
    }

    const [year, month, day] = date.split('-').map(Number);
    if (!year || !month || !day) return null;

    return { year, month, day };
}

function isBeforeMonth(date, year, month) {
    return date.year < year || (date.year === year && date.month < month);
}

function isDashboardExpense(transaction, categories) {
    const category = categories.find(item => item.id === transaction.category);
    return !(category && category.ignore);
}

async function setMonthlyExpensesChartMode(mode) {
    const barCanvas = document.getElementById('expenses-bar-chart');
    const lineCanvas = document.getElementById('monthly-expenses-line-chart');
    if (!barCanvas || !lineCanvas || !monthlyExpensesChartToggle) return;

    activeExpensesChart = mode;

    if (mode === 'line') {
        sessionStorage.removeItem('bar_label_clicked');
        sessionStorage.setItem('bar_chart_level', 'categories');
        await updateBarChart(barChart);
        drawMonthlyExpensesLineChart();
        barCanvas.style.display = 'none';
        lineCanvas.style.display = 'block';
        monthlyExpensesChartToggle.innerHTML = '<i class="fa-solid fa-chart-column"></i>';
        monthlyExpensesChartToggle.setAttribute('title', 'Gastos por categoria');
        monthlyExpensesChartToggle.setAttribute('aria-label', 'Gastos por categoria');
        return;
    }

    barCanvas.style.display = 'block';
    lineCanvas.style.display = 'none';
    monthlyExpensesChartToggle.innerHTML = '<i class="fa-solid fa-chart-line"></i>';
    monthlyExpensesChartToggle.setAttribute('title', 'Gastos ao longo do mês');
    monthlyExpensesChartToggle.setAttribute('aria-label', 'Gastos ao longo do mês');
}

const resetDashboardButton = document.querySelector('#reset-dashboard-button');
resetDashboardButton.addEventListener('click', async () => {
    if (activeExpensesChart === 'line') {
        await setMonthlyExpensesChartMode('bar');
    }
    sessionStorage.removeItem('bar_label_clicked');
    sessionStorage.setItem('bar_chart_level', 'categories');
    updateBarChart(barChart);
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

if (monthlyExpensesChartToggle) {
    monthlyExpensesChartToggle.addEventListener('click', async () => {
        await setMonthlyExpensesChartMode(activeExpensesChart === 'bar' ? 'line' : 'bar');
    });

    monthlyExpensesChartToggle.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ' || event.key === 'Spacebar') {
            event.preventDefault();
            monthlyExpensesChartToggle.click();
        }
    });
}
