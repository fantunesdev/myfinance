import * as graphicsData from '../../data/categories-report.js';

export function drawBarChart(dataset, label) {
    const father = document.getElementById('expenses-bar-chart').getContext('2d');
    const data = {
        type: 'bar',
        data: {
            labels: dataset.names,
            datasets: [{
                label: label,
                data: dataset.values,
                backgroundColor: dataset.colors
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginZero: true
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                title: {
                    display: true,
                    text: label,
                    font: {
                        size: 18
                    }
                }
            }
        }
    };
    
    return new Chart(father, data);
};


export function drawDoughnutChart(dataset, fatherHtmlId, label) {
    const father = document.getElementById(`${fatherHtmlId}-doughnut-chart`).getContext('2d');
    const data = {
        type: 'doughnut',
        data: {
            labels: dataset.names,
            backgroundColor: 'rgba(0, 0, 0, 1)',
            datasets: [{
                label: label,
                data: dataset.values,
                backgroundColor: dataset.colors,
                borderWidth: 4,
                borderColor: 'rgba(50, 50, 50, 0.2)',
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: false
                },
                title: {
                    display: true,
                    text: label,
                    font: {
                        size: 18
                    }
                }
            }
        }
    };

    new Chart(father, data);
};


function addData(chart, label, data) {
    chart.data.labels.push(label);
    chart.data.datasets.forEach((dataset) => {
        dataset.data.push(data);
    });
    chart.update();
};


function removeData(chart) {
    chart.data.labels.pop();
    chart.data.datasets.forEach((dataset) => {
        dataset.data.pop();
    });
    chart.update();
};


export function updateChart(chart, dataset) {
    let max = chart.data.labels.length,
        i;

    for (i = 0; i < max; i++) {
        removeData(chart);
    };

    for (i = 0; i < dataset.names.length; i++) {
        addData(chart, dataset.names[i], dataset.values[i]);
    };
}

