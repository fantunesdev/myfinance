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

/**
 * Busca todas as informações para desenhar os gráficos de linhas do demonstrativo anual.
 * @returns - Um gráfico de linhas.
 */
async function drawAnnualStatementChart(select) {
    await destroyCharts();

    const year = yearSeletct.value;
    const transactions = await services.getTransactionsByYear(year);
    
    const monthlyReport = monthsData.setMontlyReport(transactions);
    const lineDataset = monthsData.setMonthDataset(monthlyReport[select]);
    const doughnutDataset = monthsData.setDoughnutDataset(monthlyReport);

    const lineChart = graphics.drawLineChart(lineDataset, handleLabel(select));
    const doughnutChart = doughnut.drawDoughnutChart(doughnutDataset, 'Receitas / Despesas / Investimentos', handleAnnualStatementDoughnutClick);

    window.lineChart = lineChart;
    window.doughnutChart = doughnutChart;

    return lineChart, doughnutChart;
}

async function drawAnnualOverviewChart(select) {
    await destroyCharts();

    const transactions = await services.getResource('transactions');
    const annualReport = annualData.setAnnualReport(transactions);
    const lineDataset = annualData.setAnnualDataset(annualReport[select]);
    const doughnutDataset = monthsData.setDoughnutDataset(annualReport);

    const lineChart = graphics.drawLineChart(lineDataset, handleLabel(select));
    const doughnutChart = doughnut.drawDoughnutChart(doughnutDataset, 'Receitas / Despesas / Investimentos', handleAnnualSOverviewDoughnutClick);

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
        option.value = key;
        select.appendChild(option);
    }
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
    drawAnnualStatementChart()
});
decreaseButton.addEventListener('click', () => {
    yearSeletct.value --;
    drawAnnualStatementChart('revenues');
});
increaseButton.addEventListener('click', () => {
    yearSeletct.value ++;
    drawAnnualStatementChart('revenues');
});


annualStatementTab.addEventListener('click', () => {
    drawAnnualStatementChart('revenues');
});
annualOverviewTab.addEventListener('click', () => {
    drawAnnualOverviewChart('revenues');
});
expensesCategoryTab.addEventListener('click', () => {
    destroyCharts();
    drawExpensesCategoryChart();
    alert('Em construção');
});


let lineChart = await drawAnnualStatementChart('revenues');