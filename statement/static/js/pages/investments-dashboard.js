import * as stackedAreaChart from '../layout/elements/staked-area-chart.js';

const datasetsElement = document.getElementById('investment-progression-datasets');
const datasets = datasetsElement ? JSON.parse(datasetsElement.textContent) : [];
const interestDatasetsElement = document.getElementById('investment-interest-datasets');
const interestDatasets = interestDatasetsElement ? JSON.parse(interestDatasetsElement.textContent) : [];

if (datasets.length && datasets[0].names.length) {
    window.investmentProgressionChart = stackedAreaChart.drawStackedAreaChart(
        datasets,
        'Evolução Patrimonial'
    );
}

if (interestDatasets.length && interestDatasets[0].names.length) {
    const canvas = document.getElementById('interest-chart');
    const formatter = new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL',
    });

    window.investmentInterestChart = new Chart(canvas.getContext('2d'), {
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
                fill: dataset.label === 'Juros líquidos',
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
                    text: 'Juros e Rendimentos',
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
