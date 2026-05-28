import * as stackedAreaChart from '../layout/elements/staked-area-chart.js';

const datasetsElement = document.getElementById('investment-progression-datasets');
const datasets = datasetsElement ? JSON.parse(datasetsElement.textContent) : [];

if (datasets.length && datasets[0].names.length) {
    window.investmentProgressionChart = stackedAreaChart.drawStackedAreaChart(
        datasets,
        'Evolução Patrimonial'
    );
}
