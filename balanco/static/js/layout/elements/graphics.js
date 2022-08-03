import * as graphicsData from '../../data/categories-report.js';

export async function drawBarChart(dataset, label) {
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
            scales: {
                y: {
                    beginZero: true
                }
            }
        }
    }
    
    return new Chart(father, data);
};


export async function drawDoughnutChart(dataset, fatherHtmlId, label) {
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
    }

    new Chart(father, data);
}