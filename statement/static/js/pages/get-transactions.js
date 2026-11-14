import * as categoryData from '../data/categories-report.js';
import * as subcategoryData from '../data/subcategory-expenses.js';
import * as dataTable from '../data/expenses-table.js';
import * as graphics from '../layout/elements/graphics.js?v=20261108-2';
import * as tables from '../layout/elements/tables.js';
import * as services from '../data/services.js';
import { originalTable, statementBox } from '../layout/elements/get-transactions-elements.js';
import * as transactionObjectConversor from '../data/transactions-object-conversor.js';
import * as objectToCSVConversor from '../data/objectToCsvConversor.js';
import * as general from '../data/general.js';
import * as chartPolicy from '../data/chart-policy.js';

const yearNavigation = document.getElementById('id_year'),
    monthNavigation = document.getElementById('id_month'),
    transactionDownloadButton = document.getElementById('download-transactions-button'),
    monthlyExpensesChartToggle = document.getElementById('monthly-expenses-chart-toggle');

let monthlyExpensesLineChart = null;
let activeExpensesChart = 'bar';
let monthlyExpensesLineView = 'combined';
let dashboardTransactions = [];
let barChart = null;
let barChartUpdateVersion = 0;

function getVisibleTransactions(transactions) {
    const hiddenIds = new Set(Array.from(
        originalTable.querySelectorAll('tbody tr.row-hidden[data-tx-id]'),
        row => row.getAttribute('data-tx-id')
    ));
    return transactions.filter(transaction => !hiddenIds.has(String(transaction.id)));
}

/**
 * Busca todas as informações para desenhar os gráficos de barras e de donuts.
 * @returns - Um gráfico de barras.
 */
async function draw() {
    // busca todas as informações, classifica e faz os cálculos para montar os gráficos.
    const [year, month] = await categoryData.getMonthYear(),
        transactions = await services.getTransactionsByYearAndMonth(year, month),
        categories = await services.getResource('categories'),
        subcategories = await services.getResource('subcategories');

    sessionStorage.setItem('subcategories', JSON.stringify(subcategories));

    const report = categoryData.setCategoriesReport(transactions, categories),
        revenue = categoryData.setCategoriesDataset(report.revenue, true),
        expenses = categoryData.setCategoriesDataset(
            categoryData.setCategoriesReport(getVisibleTransactions(transactions), categories).expenses
        ),
        amount = categoryData.setAmountDataset(report.amount);

    dashboardTransactions = transactions;

    const barChart = graphics.drawBarChart(expenses, 'Despesas', updateBarChart);
    graphics.drawDoughnutChart(revenue, 'revenue', 'Receitas');
    graphics.drawDoughnutChart(amount, 'amount', 'Receitas/Despesas');

    return barChart;
}

/**
 * Atualiza o gráfico de barras conforme a categoria selecionada.
 * @param {Object} barChart - A instância original do gráfico de barras
 */
export async function updateBarChart(barChart) {
    const version = ++barChartUpdateVersion;
    const transactions = getVisibleTransactions(JSON.parse(sessionStorage.getItem('transactions'))),
        categories = JSON.parse(sessionStorage.getItem('categories'));
    const barLabelClicked = sessionStorage.getItem('bar_label_clicked');
    const category = categories.find(category => category.description === barLabelClicked);
    let expenses;

    if (category) {
        expenses = await subcategoryData.setSubcategoryDataset(category.id, transactions);
    } else {
        sessionStorage.removeItem('bar_subcategory_clicked');
        if (barLabelClicked) {
            sessionStorage.removeItem('bar_label_clicked');
            sessionStorage.setItem('bar_chart_level', 'categories');
        }
        expenses = categoryData.setCategoriesReport(transactions, categories).expenses;
    }

    if (version !== barChartUpdateVersion) return;
    const dataset = categoryData.setCategoriesDataset(expenses);
    graphics.updateChart(barChart, dataset);

    await updateTable(transactions, expenses, version);
}

/**
 * Atualiza a tabela com os registros de
 * @param {Array} transactions - Uma lista de lançamentos.
 * @param {Array} expenses - Uma lista de subcategorias do tipo despesas.
 */
async function updateTable(transactions, expenses, version) {
    let subcategoryTable = document.getElementById('subcategory-table'),
        barLabelClicked = sessionStorage.getItem('bar_label_clicked');

    if (subcategoryTable) {
        subcategoryTable.parentNode.removeChild(subcategoryTable);
    }

    if (barLabelClicked) {
        let categories = JSON.parse(sessionStorage.getItem('categories')),
            selectedCategory;

        for (let category of categories) {
            if (category.description == barLabelClicked) {
                selectedCategory = category;
            }
        }

        const lookupOptions = { forceRefresh: true };
        const accounts = await services.getResource('accounts', null, lookupOptions);
        const cards = await services.getResource('cards', null, lookupOptions);
        const banks = await services.getResource('banks', null, lookupOptions);

        if (version !== barChartUpdateVersion) return;
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
                const subcategoryLabel = sessionStorage.getItem('bar_subcategory_clicked');
                if (subcategoryLabel) {
                    const subcategory = expenses.find(expense => expense.name === subcategoryLabel);
                    filteredTransactions = filteredTransactions.filter(
                        transaction => subcategory && String(transaction.subcategory) === String(subcategory.id)
                    );
                }

                tables.renderTable(statementBox, filteredTransactions, transactionAttrs);
            }
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
    const shouldFillMobileChartHeight = window.matchMedia && window.matchMedia('(max-width: 600px)').matches;

    if (monthlyExpensesLineChart) {
        monthlyExpensesLineChart.destroy();
        monthlyExpensesLineChart = null;
    }
    // Chart.js restaura o display original do canvas ao destruir a instância.
    canvas.style.display = 'block';

    const categories = JSON.parse(sessionStorage.getItem('categories') || '[]');
    const dataset = setMonthlyExpensesLineDataset(getVisibleTransactions(dashboardTransactions), categories, monthlyExpensesLineView);
    const titles = { combined: 'Gastos consolidados', card: 'Gastos no cartão', cash: 'Gastos à vista' };
    const title = titles[monthlyExpensesLineView];
    const description = document.getElementById('monthly-expenses-line-description');
    if (description) description.textContent = dataset.description;
    const summary = document.getElementById('monthly-expenses-line-summary');
    if (summary) {
        const currency = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
        summary.textContent = `Saldo inicial: ${currency.format(dataset.initialBalance)} · Total nesta visão: ${currency.format(dataset.values.at(-1) || 0)}`;
    }

    monthlyExpensesLineChart = new Chart(canvas.getContext('2d'), {
        type: 'line',
        data: {
            labels: dataset.names,
            datasets: [
                {
                    label: title,
                    data: dataset.values,
                    borderColor: 'rgba(139, 0, 0, 1)',
                    backgroundColor: 'rgba(139, 0, 0, 0.15)',
                    fill: true,
                    tension: 0,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: !shouldFillMobileChartHeight,
            scales: {
                y: {
                    beginAtZero: true,
                },
            },
            plugins: {
                legend: {
                    display: false,
                },
                title: {
                    display: true,
                    text: title,
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

function setMonthlyExpensesLineDataset(transactions, categories, view = 'combined') {
    const [year, month] = sessionStorage.getItem('year-month').split(',').map(Number);
    const monthStart = Date.UTC(year, month - 1, 1);
    const monthEnd = Date.UTC(year, month, 0);
    const expenses = transactions.filter(transaction => transaction.type !== 'entrada'
        && isDashboardExpense(transaction, categories)
        && (view === 'combined' || getExpenseKind(transaction) === view));
    const purchases = [];
    let initialBalance = 0;
    for (const transaction of expenses) {
        const date = getMonthlyExpenseDate(transaction);
        if (isPreviousInstallment(transaction)) {
            initialBalance += Number(transaction.value || 0);
        } else if (date !== null) {
            purchases.push({ date, value: Number(transaction.value || 0) });
        }
    }
    purchases.sort((a, b) => a.date - b.date);

    if (view === 'combined') {
        let accumulated = initialBalance;
        return {
            initialBalance,
            names: ['Saldo inicial', ...purchases.map(purchase => formatExpenseDay(purchase.date))],
            values: [initialBalance, ...purchases.map(purchase => accumulated += purchase.value)],
            description: 'Parcelas anteriores no saldo inicial; demais compras na ordem da tabela.',
        };
    }

    let start = view === 'cash' ? monthStart : null;
    let end = view === 'cash' ? monthEnd : null;
    if (view === 'card') {
        for (const transaction of expenses) {
            const cycle = transaction.expense_chart;
            const cycleStart = getMonthlyExpenseDate({ posted_date: cycle?.cycle_start });
            const cycleEnd = getMonthlyExpenseDate({ posted_date: cycle?.cycle_end });
            if (cycleStart === null || cycleEnd === null) continue;
            start = start === null ? cycleStart : Math.min(start, cycleStart);
            end = end === null ? cycleEnd : Math.max(end, cycleEnd);
        }
    }
    // Preserva também datas de compras antigas/importadas fora do ciclo cadastrado.
    for (const purchase of purchases) {
        start = start === null ? purchase.date : Math.min(start, purchase.date);
        end = end === null ? purchase.date : Math.max(end, purchase.date);
    }
    start ??= monthStart;
    end ??= monthEnd;
    const daily = new Map();
    for (const purchase of purchases) daily.set(purchase.date, (daily.get(purchase.date) || 0) + purchase.value);
    const names = [];
    const values = [];
    let accumulated = initialBalance;
    for (let date = start; date <= end; date += 86400000) {
        names.push(formatExpenseDay(date));
        accumulated += daily.get(date) || 0;
        values.push(accumulated);
    }
    return {
        names, values, initialBalance,
        description: expenses.length === 0 ? 'Nenhum gasto nesta visão.' : view === 'card'
            ? 'Compras por dia nos ciclos das faturas; parcelas anteriores no saldo inicial.'
            : 'Gastos à vista por dia; parcelas anteriores no saldo inicial.',
    };
}

function getExpenseKind(transaction) {
    return transaction.expense_chart?.kind || (transaction.card || transaction.card_number ? 'card' : 'cash');
}

function isPreviousInstallment(transaction) {
    return Boolean(transaction.installment || transaction.installment_id || Number(transaction.installments_number) > 1)
        && Number(transaction.paid) > 1;
}

function formatExpenseDay(date) {
    return String(new Date(date).getUTCDate()).padStart(2, '0');
}

function getMonthlyExpenseDate(transaction) {
    const postedDate = parseDbDateParts(transaction.posted_date);
    if (!postedDate) return null;

    const date = new Date(Date.UTC(postedDate.year, postedDate.month - 1, postedDate.day));
    if (date.getUTCFullYear() !== postedDate.year || date.getUTCMonth() + 1 !== postedDate.month
        || date.getUTCDate() !== postedDate.day) return null;

    return date.getTime();
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

function isDashboardExpense(transaction, categories) {
    return chartPolicy.showInMonthlyExpenseLine(transaction);
}

async function setMonthlyExpensesChartMode(mode) {
    const barCanvas = document.getElementById('expenses-bar-chart');
    const lineCanvas = document.getElementById('monthly-expenses-line-chart');
    if (!barCanvas || !lineCanvas || !monthlyExpensesChartToggle) return;

    activeExpensesChart = mode;
    const lineControls = document.getElementById('monthly-expenses-line-controls');
    if (lineControls) lineControls.hidden = mode !== 'line';

    if (mode === 'line') {
        sessionStorage.removeItem('bar_label_clicked');
        sessionStorage.setItem('bar_chart_level', 'categories');
        await updateBarChart(barChart);
        barCanvas.style.display = 'none';
        lineCanvas.style.display = 'block';
        drawMonthlyExpensesLineChart();
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

window.addEventListener('myfinance:transaction-visibility-changed', async event => {
    if (event.detail.table !== originalTable || !barChart) return;
    await updateBarChart(barChart);
    if (activeExpensesChart === 'line') drawMonthlyExpensesLineChart();
});

barChart = await draw();
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

const monthlyExpensesLineViews = ['combined', 'card', 'cash'];
for (const view of monthlyExpensesLineViews) {
    const button = document.getElementById(`monthly-expenses-view-${view}`);
    if (!button) continue;
    button.addEventListener('click', () => {
        if (monthlyExpensesLineView === view) return;
        monthlyExpensesLineView = view;
        for (const option of monthlyExpensesLineViews) {
            const optionButton = document.getElementById(`monthly-expenses-view-${option}`);
            if (!optionButton) continue;
            optionButton.setAttribute('aria-pressed', String(option === view));
            if (option === view) optionButton.classList.add('btn-primary');
            else optionButton.classList.remove('btn-primary');
        }
        if (activeExpensesChart === 'line') drawMonthlyExpensesLineChart();
    });
}
