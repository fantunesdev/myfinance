import * as categoryData from '../data/categories-report.js';
import * as graphics from '../layout/elements/line-chart.js';
import * as doughnut from '../layout/elements/doughnut-chart.js';
import * as monthsData from '../data/months-report.js';
import * as annualData from '../data/annual-report.js';
import * as services from '../data/services.js';

const yearSeletct = document.getElementById('id_year');
const decreaseButton = document.getElementById('id_decrease');
const increaseButton = document.getElementById('id_increase');
const annualStatementTab = document.getElementById('annual-statement-tab');
const annualOverviewTab = document.getElementById('annual-overview-tab');
const expensesCategoryTab = document.getElementById('expenses-category-tab');

let expensesCategoryBarChart = null;
let activeDashboardTab = 'annual-statement';

/**
 * Busca todas as informações para desenhar os gráficos de linhas do demonstrativo anual.
 * @returns - Um gráfico de linhas.
 */
async function drawAnnualStatementChart(select) {
    await destroyCharts();

    const year = yearSeletct.value;
    const expands = { expand: 'category,card,card_number' };
    const transactions = await services.getTransactionsByYear(year, expands);

    const monthlyReport = monthsData.setMontlyReport(transactions);
    const lineDataset = monthsData.setMonthDataset(monthlyReport[select]);
    const doughnutDataset = monthsData.setDoughnutDataset(monthlyReport);

    const lineChart = graphics.drawLineChart(lineDataset, handleLabel(select));
    const doughnutChart = doughnut.drawDoughnutChart(
        doughnutDataset,
        'Receitas / Despesas / Investimentos',
        handleAnnualStatementDoughnutClick
    );

    window.lineChart = lineChart;
    window.doughnutChart = doughnutChart;

    return lineChart, doughnutChart;
}

async function drawAnnualOverviewChart(select) {
    await destroyCharts();

    const expands = { expand: 'card_number' };
    const transactions = await services.getResource('transactions', expands);
    const annualReport = annualData.setAnnualReport(transactions);
    const lineDataset = annualData.setAnnualDataset(annualReport[select]);
    const doughnutDataset = monthsData.setDoughnutDataset(annualReport);

    const lineChart = graphics.drawLineChart(lineDataset, handleLabel(select));
    const doughnutChart = doughnut.drawDoughnutChart(
        doughnutDataset,
        'Receitas / Despesas / Investimentos',
        handleAnnualSOverviewDoughnutClick
    );

    window.lineChart = lineChart;
    window.doughnutChart = doughnutChart;

    return lineChart, doughnutChart;
}

async function destroyCharts() {
    // Restaurar visibilidade dos gráficos
    const lineChart = document.getElementById('line-chart').parentElement;
    const doughnutChart = document.getElementById('donnut-chart').parentElement;
    const expensesCategoryChart = document.querySelector('.expenses-category-chart');

    if (lineChart) lineChart.style.display = 'block';
    if (doughnutChart) doughnutChart.style.display = 'block';
    if (expensesCategoryChart) expensesCategoryChart.style.display = 'none';

    // Limpar tabela
    const tableContainer = document.getElementById('expenses-category-table-container');
    if (tableContainer) {
        tableContainer.style.display = 'none';
        tableContainer.innerHTML = '';
    }

    if (window.lineChart) {
        await window.lineChart.destroy();
        window.lineChart = null;
    }
    if (window.doughnutChart) {
        await window.doughnutChart.destroy();
        window.doughnutChart = null;
    }
    if (window.expensesCategoryBarChart) {
        await window.expensesCategoryBarChart.destroy();
        window.expensesCategoryBarChart = null;
        expensesCategoryBarChart = null;
    }
}

async function drawExpensesCategoryChart() {
    if (window.expensesCategoryBarChart) {
        window.expensesCategoryBarChart.destroy();
        window.expensesCategoryBarChart = null;
    }

    // Mostrar o canvas de gastos por categoria
    const lineChart = document.getElementById('line-chart').parentElement;
    const doughnutChart = document.getElementById('donnut-chart').parentElement;
    const expensesCategoryChart = document.querySelector('.expenses-category-chart');

    if (lineChart) lineChart.style.display = 'none';
    if (doughnutChart) doughnutChart.style.display = 'none';
    if (expensesCategoryChart) expensesCategoryChart.style.display = 'block';

    const year = yearSeletct.value;
    const expands = { expand: 'category,subcategory,card,card_number,account' };
    const transactions = await services.getTransactionsByYear(year, expands);
    const categories = await services.getResource('categories');

    // Normalizar IDs sem perder os nomes usados no detalhe da tabela.
    const normalizedTransactions = transactions.map(t => ({
        ...t,
        category: getResourceId(t.category),
        category_name: getResourceDescription(t.category),
        subcategory: getResourceId(t.subcategory),
        subcategory_name: getResourceDescription(t.subcategory),
        card_name: getPaymentDescription(t),
    }));

    const report = categoryData.setCategoriesReport(normalizedTransactions, categories);
    const expenses = categoryData.setCategoriesDataset(report.expenses);

    // Salvar dados para uso posterior
    sessionStorage.setItem('annual_transactions', JSON.stringify(normalizedTransactions));
    sessionStorage.setItem('annual_categories', JSON.stringify(categories));
    sessionStorage.removeItem('annual_subcategories');
    sessionStorage.removeItem('subcategory_map');
    sessionStorage.setItem('bar_chart_level', 'categories');
    sessionStorage.removeItem('bar_label_clicked');

    const canvasElement = document.getElementById('expenses-category-bar-chart');
    const father = canvasElement.getContext('2d');

    expensesCategoryBarChart = new Chart(father, {
        type: 'bar',
        data: {
            labels: expenses.names,
            datasets: [
                {
                    label: 'Despesas por Categoria',
                    data: expenses.values,
                    backgroundColor: expenses.colors,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
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
                    text: 'Gastos por Categoria',
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
            onClick: handleExpensesCategoryBarClick,
            onHover: handleBarHover,
        },
    });

    window.expensesCategoryBarChart = expensesCategoryBarChart;
}

/**
 * Trata o evento do click no gráfico de categorias
 */
async function handleExpensesCategoryBarClick(event, elements) {
    if (!expensesCategoryBarChart) return;

    if (!elements.length) {
        const barChartLevel = sessionStorage.getItem('bar_chart_level');
        if (barChartLevel === 'subcategories') {
            sessionStorage.removeItem('bar_label_clicked');
            sessionStorage.removeItem('bar_category_id');
            sessionStorage.removeItem('subcategory_map');
            sessionStorage.removeItem('annual_subcategories');
            sessionStorage.setItem('bar_chart_level', 'categories');
            await updateExpensesCategoryChart();
        }
        return;
    }

    if (elements.length > 0) {
        const clickedIndex = elements[0].index;
        const labelClicked = expensesCategoryBarChart.data.labels[clickedIndex];
        const barChartLevel = sessionStorage.getItem('bar_chart_level');

        if (barChartLevel === 'subcategories') {
            // Renderizar tabela da subcategoria clicada
            const subcategoryMap = JSON.parse(sessionStorage.getItem('subcategory_map') || '{}');
            const subcategoryId = subcategoryMap[labelClicked];
            if (subcategoryId) {
                renderExpensesCategoryTable(labelClicked, subcategoryId, 'subcategories');
            }
        } else {
            // Mostrar subcategorias da categoria clicada
            const categories = JSON.parse(sessionStorage.getItem('annual_categories'));
            let categoryId = null;
            for (let category of categories) {
                if (category.description === labelClicked) {
                    categoryId = category.id;
                    break;
                }
            }

            if (!categoryId) return;

            sessionStorage.setItem('bar_label_clicked', labelClicked);
            sessionStorage.setItem('bar_category_id', categoryId);
            sessionStorage.setItem('bar_chart_level', 'subcategories');
            await updateExpensesCategoryChart();

            // Renderizar tabela com transações da categoria
            renderExpensesCategoryTable(labelClicked, categoryId, 'categories');
        }
    }
}

/**
 * Atualiza o gráfico de despesas por categorias/subcategorias
 */
async function updateExpensesCategoryChart() {
    const transactionsStr = sessionStorage.getItem('annual_transactions');
    const categoriesStr = sessionStorage.getItem('annual_categories');

    const transactions = JSON.parse(transactionsStr);
    const categories = JSON.parse(categoriesStr);
    const barChartLevel = sessionStorage.getItem('bar_chart_level');
    const barLabelClicked = sessionStorage.getItem('bar_label_clicked');

    let expenses;

    if (barLabelClicked && barChartLevel === 'subcategories') {
        // Buscar subcategorias da categoria clicada
        let selectedCategory = null;
        for (let category of categories) {
            if (category.description === barLabelClicked) {
                selectedCategory = category;
                break;
            }
        }

        if (selectedCategory) {
            // Buscar subcategorias dessa categoria
            const subcategories = await services.getChildrenResource('categories', 'subcategories', selectedCategory.id);

            // Calcular valores por subcategoria
            const subcategoryData = [];
            const subcategoryMap = {};

            for (let subcategory of subcategories) {
                let amount = 0;
                for (let transaction of transactions) {
                    if (transaction.subcategory === subcategory.id) {
                        amount += transaction.value;
                    }
                }
                if (amount > 0) {
                    subcategoryData.push({
                        id: subcategory.id,
                        name: subcategory.description,
                        amount: amount,
                    });
                    subcategoryMap[subcategory.description] = subcategory.id;
                }
            }

            // Ordenar por quantidade decrescente
            subcategoryData.sort((a, b) => (a.amount < b.amount ? 1 : a.amount > b.amount ? -1 : 0));

            expenses = categoryData.setCategoriesDataset(subcategoryData);

            // Guardar mapa de subcategorias para uso posterior
            sessionStorage.setItem('subcategory_map', JSON.stringify(subcategoryMap));
            sessionStorage.setItem('annual_subcategories', JSON.stringify(subcategories));
        } else {
            // Se não encontrar categoria, voltar para categorias
            const report = categoryData.setCategoriesReport(transactions, categories);
            expenses = categoryData.setCategoriesDataset(report.expenses);
            sessionStorage.removeItem('bar_label_clicked');
            sessionStorage.setItem('bar_chart_level', 'categories');
        }
    } else {
        // Mostrar categorias
        const report = categoryData.setCategoriesReport(transactions, categories);
        expenses = categoryData.setCategoriesDataset(report.expenses);
        sessionStorage.removeItem('bar_label_clicked');
        sessionStorage.setItem('bar_chart_level', 'categories');

        // Ocultar tabela
        const tableContainer = document.getElementById('expenses-category-table-container');
        if (tableContainer) {
            tableContainer.style.display = 'none';
            tableContainer.innerHTML = '';
        }
    }

    // Atualizar o gráfico
    expensesCategoryBarChart.data.labels = expenses.names;
    expensesCategoryBarChart.data.datasets[0].data = expenses.values;
    expensesCategoryBarChart.data.datasets[0].backgroundColor = expenses.colors;
    expensesCategoryBarChart.update();
}

/**
 * Trata o evento do hover fazendo com que o cursor se torne pointer quando passa por uma das barras.
 */
function handleBarHover(event, elements) {
    if (expensesCategoryBarChart) {
        expensesCategoryBarChart.canvas.style.cursor = elements && elements.length > 0 ? 'pointer' : 'default';
    }
}

/**
 * Renderiza a tabela com as transações da categoria/subcategoria clicada
 */
function renderExpensesCategoryTable(itemName, itemId, itemType = 'categories') {
    const transactions = JSON.parse(sessionStorage.getItem('annual_transactions') || '[]');

    // Filtrar transações
    let filteredTransactions = [];

    if (itemType === 'categories') {
        // Filtrar por categoria
        filteredTransactions = transactions.filter(t => t.category === itemId);
    } else {
        // Filtrar por subcategoria
        filteredTransactions = transactions.filter(t => t.subcategory === itemId);
    }

    // Ordenar por data decrescente
    filteredTransactions.sort((a, b) => new Date(b.posted_date) - new Date(a.posted_date));

    // Gerar HTML da tabela
    const tableHTML = generateExpensesTableHTML(filteredTransactions, itemName);

    // Inserir na página
    const tableContainer = document.getElementById('expenses-category-table-container');
    if (tableContainer) {
        tableContainer.innerHTML = tableHTML;
        tableContainer.style.display = 'block';
    }
}

/**
 * Gera o HTML da tabela de transações
 */
function generateExpensesTableHTML(transactions, categoryName) {
    if (transactions.length === 0) {
        return `
            <div class="expenses-category-table-empty">
                Nenhuma transação encontrada para <strong>${escapeHtml(categoryName)}</strong>
            </div>
        `;
    }

    const totalValue = transactions.reduce((total, transaction) => total + Number(transaction.value || 0), 0);

    let tableHTML = `
        <div class="expenses-category-table">
            <div class="expenses-category-table-header">
                <h4>Transações de <strong>${escapeHtml(categoryName)}</strong> (${transactions.length})</h4>
                <strong>${formatCurrency(totalValue)}</strong>
            </div>
            <table class="table table-striped">
                <thead>
                    <tr>
                        <th>Data</th>
                        <th>Descrição</th>
                        <th>Categoria</th>
                        <th>Subcategoria</th>
                        <th>Meio de Pagamento</th>
                        <th class="numeric">Valor</th>
                    </tr>
                </thead>
                <tbody>
    `;

    transactions.forEach(transaction => {
        tableHTML += `
            <tr>
                <td>${escapeHtml(formatDate(transaction.posted_date))}</td>
                <td>${escapeHtml(transaction.description || '-')}</td>
                <td>${escapeHtml(transaction.category_name || getCategoryName(transaction.category) || '-')}</td>
                <td>${escapeHtml(transaction.subcategory_name || getSubcategoryName(transaction.subcategory) || '-')}</td>
                <td>${escapeHtml(transaction.card_name || '-')}</td>
                <td class="numeric">${formatCurrency(transaction.value)}</td>
            </tr>
        `;
    });

    tableHTML += `
                </tbody>
                <tfoot>
                    <tr>
                        <td colspan="5" class="numeric">TOTAL:</td>
                        <td class="numeric">${formatCurrency(totalValue)}</td>
                    </tr>
                </tfoot>
            </table>
        </div>
    `;

    return tableHTML;
}

function getResourceId(resource) {
    return typeof resource === 'object' && resource !== null ? resource.id : resource;
}

function getResourceDescription(resource) {
    if (typeof resource !== 'object' || resource === null) return '';
    return resource.description || resource.name || resource.number || '';
}

function getPaymentDescription(transaction) {
    const cardDescription = getResourceDescription(transaction.card);
    const cardNumberDescription = getResourceDescription(transaction.card_number);
    const accountDescription = getResourceDescription(transaction.account);

    if (cardDescription && cardNumberDescription) {
        return `${cardDescription} - ${cardNumberDescription}`;
    }
    if (cardDescription) return cardDescription;
    if (accountDescription) return accountDescription;

    return transaction.payment_method_display || '-';
}

function getCategoryName(categoryId) {
    const categories = JSON.parse(sessionStorage.getItem('annual_categories') || '[]');
    const category = categories.find(item => item.id === categoryId);
    return category ? category.description : '';
}

function getSubcategoryName(subcategoryId) {
    const subcategories = JSON.parse(sessionStorage.getItem('annual_subcategories') || '[]');
    const subcategory = subcategories.find(item => item.id === subcategoryId);
    return subcategory ? subcategory.description : '';
}

function formatDate(date) {
    if (!date) return '-';
    return date.split('-').reverse().join('/');
}

function formatCurrency(value) {
    return Number(value || 0).toLocaleString('pt-BR', {
        style: 'currency',
        currency: 'BRL',
    });
}

function escapeHtml(value) {
    const element = document.createElement('span');
    element.textContent = value;
    return element.innerHTML;
}

function handleLabel(select) {
    if (select == 'revenues') {
        return 'Receitas';
    } else if (select == 'expenses') {
        return 'Despesas';
    } else {
        return 'Investimentos';
    }
}

function handleAnnualStatementDoughnutClick(newSelect) {
    let select = newSelect;
    drawAnnualStatementChart(select);
}

function handleAnnualSOverviewDoughnutClick(newSelect) {
    let select = newSelect;
    drawAnnualOverviewChart(select);
}

yearSeletct.addEventListener('change', () => {
    if (activeDashboardTab === 'expenses-category') {
        drawExpensesCategoryChart();
    } else if (activeDashboardTab === 'annual-overview') {
        drawAnnualOverviewChart('revenues');
    } else {
        drawAnnualStatementChart('revenues');
    }
});
decreaseButton.addEventListener('click', () => {
    yearSeletct.value--;
    if (activeDashboardTab === 'expenses-category') {
        drawExpensesCategoryChart();
    } else if (activeDashboardTab === 'annual-overview') {
        drawAnnualOverviewChart('revenues');
    } else {
        drawAnnualStatementChart('revenues');
    }
});
increaseButton.addEventListener('click', () => {
    yearSeletct.value++;
    if (activeDashboardTab === 'expenses-category') {
        drawExpensesCategoryChart();
    } else if (activeDashboardTab === 'annual-overview') {
        drawAnnualOverviewChart('revenues');
    } else {
        drawAnnualStatementChart('revenues');
    }
});

annualStatementTab.addEventListener('click', () => {
    activeDashboardTab = 'annual-statement';
    drawAnnualStatementChart('revenues');
});
annualOverviewTab.addEventListener('click', () => {
    activeDashboardTab = 'annual-overview';
    drawAnnualOverviewChart('revenues');
});
expensesCategoryTab.addEventListener('click', async () => {
    activeDashboardTab = 'expenses-category';
    await destroyCharts();
    drawExpensesCategoryChart();
});

let lineChart = await drawAnnualStatementChart('revenues');
