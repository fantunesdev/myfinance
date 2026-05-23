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
    const transactions = await services.getTransactionsByYear(year, expands, true);
    const visibleTransactions = Array.isArray(transactions) ? transactions.filter(isHomeScreenTransaction) : [];

    const monthlyReport = monthsData.setMontlyReport(visibleTransactions);
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
    await services.getResource('categories');

    const visibleTransactions = Array.isArray(transactions) ? transactions.filter(isHomeScreenTransaction) : [];
    const annualReport = annualData.setAnnualReport(visibleTransactions);
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
    const transactions = await services.getTransactionsByYear(year, expands, true);
    const categories = await services.getResource('categories');
    const visibleTransactions = Array.isArray(transactions) ? transactions.filter(isHomeScreenTransaction) : [];

    // Normalizar IDs sem perder os nomes usados no detalhe da tabela.
    const normalizedTransactions = visibleTransactions.map(t => ({
        ...t,
        category: getResourceId(t.category),
        category_name: getResourceDescription(t.category),
        category_color: getCategoryColor(t.category),
        category_icon: getCategoryIcon(t.category),
        subcategory: getResourceId(t.subcategory),
        subcategory_name: getResourceDescription(t.subcategory),
        card_name: getPaymentDescription(t),
        payment_icon: getPaymentIcon(t),
        payment_url: getPaymentUrl(t),
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
        initializeExpensesCategoryTableSort(tableContainer);
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
            <table class="table" id="expenses-category-statement-table">
                <thead>
                    <tr>
                        <th class="sortable">Data <span class="sort-btn" data-field="0" role="button" tabindex="0" aria-label="Ordenar"><i class="fa-solid fa-sort"></i></span></th>
                        <th class="sortable">Banco/Cartão <span class="sort-btn" data-field="1" role="button" tabindex="0" aria-label="Ordenar"><i class="fa-solid fa-sort"></i></span></th>
                        <th class="sortable">Categoria <span class="sort-btn" data-field="2" role="button" tabindex="0" aria-label="Ordenar"><i class="fa-solid fa-sort"></i></span></th>
                        <th class="sortable">Sub-Categoria <span class="sort-btn" data-field="3" role="button" tabindex="0" aria-label="Ordenar"><i class="fa-solid fa-sort"></i></span></th>
                        <th class="sortable">Descrição <span class="sort-btn" data-field="4" role="button" tabindex="0" aria-label="Ordenar"><i class="fa-solid fa-sort"></i></span></th>
                        <th class="sortable numeric">Valor <span class="sort-btn" data-field="5" role="button" tabindex="0" aria-label="Ordenar"><i class="fa-solid fa-sort"></i></span></th>
                        <th class="no-wrap">Ações</th>
                    </tr>
                </thead>
                <tbody>
    `;

    transactions.forEach(transaction => {
        tableHTML += `
            <tr style="border-left: solid 3px ${escapeHtml(getTransactionCategoryColor(transaction))}" data-value="${Number(transaction.value || 0)}" data-tx-id="${transaction.id || ''}">
                <td>${escapeHtml(formatDate(transaction.posted_date))}</td>
                <td>${getPaymentCellHTML(transaction)}</td>
                <td class="category-cell">${getCategoryCellHTML(transaction)}</td>
                <td>${escapeHtml(transaction.subcategory_name || getSubcategoryName(transaction.subcategory) || '-')}</td>
                <td>${escapeHtml(getTransactionDescription(transaction))}</td>
                <td class="numeric">${formatCurrency(transaction.value)}</td>
                <td>${getActionsCellHTML(transaction)}</td>
            </tr>
        `;
    });

    tableHTML += `
                </tbody>
                <tfoot>
                    <tr>
                        <td colspan="5" class="numeric">TOTAL:</td>
                        <td class="numeric">${formatCurrency(totalValue)}</td>
                        <td></td>
                    </tr>
                </tfoot>
            </table>
        </div>
    `;

    return tableHTML;
}

function initializeExpensesCategoryTableSort(container) {
    const table = container.querySelector('#expenses-category-statement-table');
    if (!table || !table.tBodies.length) return;

    const tbody = table.tBodies[0];
    const sortButtons = Array.from(table.querySelectorAll('.sort-btn'));
    const sortState = { index: null, asc: true };

    function getCellValue(row, idx) {
        if (idx === 5) return Number(row.dataset.value || 0);

        const cell = row.cells[idx];
        if (!cell) return '';

        if (idx === 0) return getDateSortValue(cell.innerText.trim());

        return cell.innerText.trim().toLowerCase();
    }

    function sortByColumn(idx) {
        const asc = sortState.index === idx ? !sortState.asc : true;
        const rows = Array.from(tbody.rows);

        rows.sort((a, b) => {
            const valueA = getCellValue(a, idx);
            const valueB = getCellValue(b, idx);

            if (typeof valueA === 'number' && typeof valueB === 'number') {
                return asc ? valueA - valueB : valueB - valueA;
            }

            return asc ? valueA.localeCompare(valueB) : valueB.localeCompare(valueA);
        });

        for (const row of rows) tbody.appendChild(row);

        sortState.index = idx;
        sortState.asc = asc;

        sortButtons.forEach(btn => {
            btn.innerHTML = '<i class="fa-solid fa-arrows-up-down action-icon"></i>';
            btn.classList.remove('active');
        });

        const activeBtn = table.querySelector(`.sort-btn[data-field="${idx}"]`);
        if (activeBtn) {
            activeBtn.innerHTML = `<i class="fa-solid ${asc ? 'fa-sort-up' : 'fa-sort-down'} action-icon"></i>`;
            activeBtn.classList.add('active');
        }
    }

    sortButtons.forEach(btn => {
        const onSort = () => {
            const idx = Number(btn.getAttribute('data-field'));
            if (Number.isNaN(idx)) return;
            sortByColumn(idx);
        };

        btn.addEventListener('click', onSort);
        btn.addEventListener('keydown', event => {
            if (event.key === 'Enter' || event.key === ' ' || event.key === 'Spacebar') {
                event.preventDefault();
                onSort();
            }
        });
    });
}

function getDateSortValue(value) {
    const [day, month, year] = value.split('/').map(Number);
    return new Date(year || Number(yearSeletct.value), (month || 1) - 1, day || 1).getTime();
}

function isHomeScreenTransaction(transaction) {
    if (!transaction.home_screen) return false;
    if (transaction.card_number && transaction.card_number.home_screen === false) return false;

    return true;
}

function getResourceId(resource) {
    return typeof resource === 'object' && resource !== null ? resource.id : resource;
}

function getResourceDescription(resource) {
    if (typeof resource !== 'object' || resource === null) return '';
    return resource.description || resource.name || resource.number || '';
}

function getCategoryColor(category) {
    if (typeof category !== 'object' || category === null) return '';
    return category.color || '';
}

function getCategoryIcon(category) {
    if (typeof category !== 'object' || category === null) return '';
    return category.icon || '';
}

function getPaymentDescription(transaction) {
    const cardDescription = getResourceDescription(transaction.card);
    const cardNumberDescription = getResourceDescription(transaction.card_number);
    const accountDescription = getResourceDescription(transaction.account) || getNestedValue(transaction.account, ['bank', 'description']);

    if (cardDescription && cardNumberDescription) {
        return `${cardDescription} - ${cardNumberDescription}`;
    }
    if (cardDescription) return cardDescription;
    if (accountDescription) return accountDescription;

    return transaction.payment_method_display || '-';
}

function getPaymentIcon(transaction) {
    const accountIcon = getNestedValue(transaction.account, ['bank', 'icon']) || getNestedValue(transaction.account, ['icon']);
    const cardIcon = getNestedValue(transaction.card, ['icon']);
    const cardNumberCardIcon = getNestedValue(transaction.card_number, ['card', 'icon']);

    return accountIcon || cardIcon || cardNumberCardIcon || '';
}

function getPaymentUrl(transaction) {
    const year = String(transaction.payment_date || transaction.posted_date || '').split('-')[0];
    const month = String(transaction.payment_date || transaction.posted_date || '').split('-')[1];
    const accountId = getResourceId(transaction.account);
    const cardId = getResourceId(transaction.card) || getNestedValue(transaction.card_number, ['card', 'id']) || getNestedValue(transaction.card_number, ['card']);

    if (accountId && year && month) {
        return `/relatorio_financeiro/contas/${accountId}/extrato/${year}/${month}/`;
    }
    if (cardId && year && month) {
        return `/relatorio_financeiro/cartoes/${cardId}/fatura/${year}/${month}/`;
    }

    return '';
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

function getTransactionCategoryColor(transaction) {
    return transaction.category_color || getCategoryColorById(transaction.category) || 'transparent';
}

function getCategoryColorById(categoryId) {
    const categories = JSON.parse(sessionStorage.getItem('annual_categories') || '[]');
    const category = categories.find(item => item.id === categoryId);
    return category ? category.color : '';
}

function getCategoryIconById(categoryId) {
    const categories = JSON.parse(sessionStorage.getItem('annual_categories') || '[]');
    const category = categories.find(item => item.id === categoryId);
    return category ? category.icon : '';
}

function getCategoryCellHTML(transaction) {
    const icon = transaction.category_icon || getCategoryIconById(transaction.category);
    const name = transaction.category_name || getCategoryName(transaction.category) || '-';
    const iconHTML = icon ? `<i class="${escapeHtml(icon)}"></i>` : '';

    return `${iconHTML} ${escapeHtml(name)}`;
}

function getPaymentCellHTML(transaction) {
    const icon = transaction.payment_icon;
    const label = getPaymentLabel(transaction);
    const content = icon ? `<img src="${escapeHtml(icon)}" alt="${escapeHtml(label)}">` : escapeHtml(label);
    const cardNumberDescription = getResourceDescription(transaction.card_number);
    const cardNumberHTML = cardNumberDescription ? `<div class="small">${escapeHtml(cardNumberDescription)}</div>` : '';

    if (transaction.payment_url) {
        return `<a href="${escapeHtml(transaction.payment_url)}">${content}</a>${cardNumberHTML}`;
    }

    return `${content}${cardNumberHTML}`;
}

function getPaymentLabel(transaction) {
    const cardDescription = getResourceDescription(transaction.card);
    const accountDescription = getResourceDescription(transaction.account) || getNestedValue(transaction.account, ['bank', 'description']);

    return cardDescription || accountDescription || transaction.card_name || '-';
}

function getTransactionDescription(transaction) {
    if (!transaction.installments_number) return transaction.description || '-';
    return `${transaction.description || '-'} (${transaction.paid}/${transaction.installments_number})`;
}

function getActionsCellHTML(transaction) {
    if (!transaction.id && !transaction.installment) return '';

    const detailUrl = transaction.installment
        ? `/relatorio_financeiro/parcelamento/${transaction.installment}/`
        : `/relatorio_financeiro/${transaction.id}/`;
    const updateUrl = transaction.installment
        ? `/relatorio_financeiro/parcelamento/editar/${transaction.installment}/`
        : `/relatorio_financeiro/editar/${transaction.id}/`;
    const deleteUrl = transaction.installment
        ? `/relatorio_financeiro/parcelamento/remover/${transaction.installment}/`
        : `/relatorio_financeiro/remover/${transaction.id}`;

    return `
        <a href="${detailUrl}"><i class="fa-solid fa-file-lines action-icon"></i></a>
        <a href="${updateUrl}"><i class="fa-solid fa-pen-to-square action-icon"></i></a>
        <a href="${deleteUrl}"><i class="fa-solid fa-trash action-icon"></i></a>
    `;
}

function getNestedValue(object, path) {
    if (typeof object !== 'object' || object === null) return '';
    return path.reduce((value, key) => {
        if (typeof value !== 'object' || value === null) return '';
        return value[key] || '';
    }, object);
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
