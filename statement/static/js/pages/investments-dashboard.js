import * as stackedAreaChart from '../layout/elements/staked-area-chart.js';

const datasetsElement = document.getElementById('investment-progression-datasets');
const datasets = datasetsElement ? JSON.parse(datasetsElement.textContent) : [];
const interestDatasetsElement = document.getElementById('investment-interest-datasets');
const interestDatasets = interestDatasetsElement ? JSON.parse(interestDatasetsElement.textContent) : [];
const chartToggle = document.getElementById('investment-chart-toggle');

let activeChart = 'progression';

function destroyInvestmentChart() {
    if (window.investmentChart) {
        window.investmentChart.destroy();
        window.investmentChart = null;
    }
}

function setChartToggleMode(mode) {
    if (!chartToggle) return;

    if (mode === 'interest') {
        chartToggle.innerHTML = '<i class="fa-solid fa-chart-area"></i>';
        chartToggle.setAttribute('title', 'Evolução patrimonial');
        chartToggle.setAttribute('aria-label', 'Evolução patrimonial');
        return;
    }

    chartToggle.innerHTML = '<i class="fa-solid fa-percent"></i>';
    chartToggle.setAttribute('title', 'Ganhos');
    chartToggle.setAttribute('aria-label', 'Ganhos');
}

function drawProgressionChart() {
    destroyInvestmentChart();
    activeChart = 'progression';
    setChartToggleMode('progression');

    if (!datasets.length || !datasets[0].names.length) return;

    window.investmentChart = stackedAreaChart.drawStackedAreaChart(
        datasets,
        'Evolução Patrimonial'
    );
}

function drawInterestChart() {
    destroyInvestmentChart();
    activeChart = 'interest';
    setChartToggleMode('interest');

    if (!interestDatasets.length || !interestDatasets[0].names.length) return;

    const canvas = document.getElementById('line-chart');
    const formatter = new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL',
    });

    window.investmentChart = new Chart(canvas.getContext('2d'), {
        type: 'line',
        data: {
            labels: interestDatasets[0].names,
            datasets: interestDatasets.map((dataset) => ({
                label: dataset.label,
                data: dataset.values,
                borderColor: dataset.color,
                backgroundColor: dataset.color.replace('1)', '0.16)'),
                borderWidth: 2,
                pointRadius: 4,
                tension: 0.2,
                fill: dataset.label === 'Resultado',
            })),
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    ticks: {
                        callback: (value) => formatter.format(value),
                    },
                },
            },
            plugins: {
                legend: {
                    display: true,
                },
                title: {
                    display: true,
                    text: 'Ganhos',
                    font: {
                        size: 18,
                        family: 'Ubuntu',
                    },
                    color: 'rgba(204,204,204,1)',
                },
                tooltip: {
                    callbacks: {
                        label: (context) => `${context.dataset.label}: ${formatter.format(context.parsed.y)}`,
                    },
                },
            },
            animation: {
                duration: 200,
            },
        },
    });
}

if (chartToggle) {
    chartToggle.addEventListener('click', () => {
        if (activeChart === 'interest') {
            drawProgressionChart();
            return;
        }

        drawInterestChart();
    });

    chartToggle.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ' || event.key === 'Spacebar') {
            event.preventDefault();
            chartToggle.click();
        }
    });
}

drawProgressionChart();
