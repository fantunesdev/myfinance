import * as categoryData from '../data/categories-report.js';
import * as graphics from '../layout/elements/line-chart.js';
import * as doughnut from '../layout/elements/doughnut-chart.js';
import * as monthsData from '../data/months-report.js';
import * as annualData from '../data/annual-report.js';
import * as services from '../data/services.js';

const dashboardSelect = document.getElementById('dashboard-select');
const yearSeletct = document.getElementById('id_year');
const decreaseButton = document.getElementById('id_decrease');
const increaseButton = document.getElementById('id_increase');
const annualStatementTab = document.getElementById('annual-statement-tab');
const annualOverviewTab = document.getElementById('annual-overview-tab');
const expensesCategoryTab = document.getElementById('expenses-category-tab');

createSelectOptions(
    dashboardSelect, 
    {
        revenues: 'Entradas',
        expenses: 'Saídas',
        investments: 'Investimentos'
    }
);

/**
 * Busca todas as informações para desenhar os gráficos de linhas do demonstrativo anual.
 * @returns - Um gráfico de barras.
 */
async function drawAnnualStatementChart() {
    await destroyCharts();

    const year = yearSeletct.value;
    const transactions = await services.getTransactionsByYear(year);
    
    const monthlyReport = monthsData.setMontlyReport(transactions);
    const lineDataset = monthsData.setMonthDataset(monthlyReport[dashboardSelect.value]);
    const doughnutDataset = monthsData.setDoughnutDataset(monthlyReport);

    const label = dashboardSelect.options[dashboardSelect.selectedIndex].innerText;
    const lineChart = graphics.drawBarChart(lineDataset, label);
    const doughnutChart = doughnut.drawDoughnutChart(doughnutDataset, 'Receitas / Despesas / Investimentos');
    window.lineChart = lineChart;
    window.doughnutChart = doughnutChart;

    return lineChart, doughnutChart;
}

async function drawAnnualOverviewChart() {
    await destroyCharts();

    const select = 'expenses';

    const transactions = await services.getResource('transactions');
    const annualReport = annualData.setAnnualReport(transactions);
    const lineDataset = annualData.setAnnualDataset(annualReport[select]);
    const doughnutDataset = monthsData.setDoughnutDataset(annualReport);

    const lineChart = graphics.drawBarChart(lineDataset, select);
    const doughnutChart = doughnut.drawDoughnutChart(doughnutDataset, 'Receitas / Despesas / Investimentos');
    window.lineChart = lineChart;
    window.doughnutChart = doughnutChart;

    return lineChart, doughnutChart;
}

async function destroyCharts() {
    if (window.lineChart) {
        await window.lineChart.destroy();
        window.lineChart = null;
    }
    if (window.doughnutChart) {
        await window.doughnutChart.destroy();
        window.doughnutChart = null;
    }
}

async function drawExpensesCategoryChart() {
    if (window.lineChart) {
        window.lineChart.destroy();
    }
}

function createSelectOptions(select, object) {
    for (const key in object) {
        const option = document.createElement('option');
        option.text = object[key];
        option.value = key
        select.appendChild(option);
    }
}

dashboardSelect.addEventListener('change', () => {
    drawAnnualStatementChart()
});
yearSeletct.addEventListener('change', () => {
    drawAnnualStatementChart()
});
decreaseButton.addEventListener('click', () => {
    yearSeletct.value --;
    drawAnnualStatementChart()
});
increaseButton.addEventListener('click', () => {
    yearSeletct.value ++;
    drawAnnualStatementChart()
});


annualStatementTab.addEventListener('click', () => {
    drawAnnualStatementChart();
});
annualOverviewTab.addEventListener('click', () => {
    drawAnnualOverviewChart();
});
expensesCategoryTab.addEventListener('click', () => {
    drawExpensesCategoryChart();
});


let lineChart = await drawAnnualStatementChart();