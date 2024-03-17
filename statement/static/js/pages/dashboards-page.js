import * as categoryData from '../data/categories-report.js';
import * as graphics from '../layout/elements/line-chart.js';
import * as monthsData from '../data/months-report.js';
import * as services from '../data/services.js';

const dashboardSelect = document.getElementById('dashboard-select');
createSelectOptions(
    dashboardSelect, 
    {
        revenues: 'Entradas',
        expenses: 'Saídas',
        investments: 'Investimentos'
    }
);

/**
 * Busca todas as informações para desenhar os gráficos de barras e de donuts.
 * @returns - Um gráfico de barras.
 */
async function draw() {
    if (window.lineChart) {
        window.lineChart.destroy();
    }
    let year = 2024;
    const transactions = await services.getTransactionsByYear(year);
    
    const monthlyReport = monthsData.setMontlyReport(transactions);
    const dataset = monthsData.setMonthDataset(monthlyReport[dashboardSelect.value])

    const label = dashboardSelect.options[dashboardSelect.selectedIndex].innerText;
    const lineChart = graphics.drawBarChart(dataset, label);
    window.lineChart = lineChart;

    return lineChart;
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
    draw()
});

let lineChart = await draw();