import * as categoryData from '../data/categories-report.js';
import * as graphics from '../layout/elements/line-chart.js';
import * as monthsData from '../data/months-report.js';
import * as services from '../data/services.js';

const dashboardSelect = document.getElementById('dashboard-select');
const yearSeletct = document.getElementById('id_year');
const decreaseButton = document.getElementById('id_decrease');
const increaseButton = document.getElementById('id_increase');

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
    const year = yearSeletct.value;
    const transactions = await services.getTransactionsByYear(year);
    
    const monthlyReport = monthsData.setMontlyReport(transactions);
    const dataset = monthsData.setMonthDataset(monthlyReport[dashboardSelect.value])

    const label = `${dashboardSelect.options[dashboardSelect.selectedIndex].innerText} ${yearSeletct.value}`;
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
yearSeletct.addEventListener('change', () => {
    draw()
});
decreaseButton.addEventListener('click', () => {
    yearSeletct.value --;
    draw()
});
increaseButton.addEventListener('click', () => {
    yearSeletct.value ++;
    draw()
});

let lineChart = await draw();