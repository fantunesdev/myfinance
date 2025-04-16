import { updateBarChart } from '../../pages/get-transactions.js';

let chart;

/**
 * Monta o gráfico de barras.
 * @param {Object} dataset - Objeto com as informações que serão usadas para montar o gráfico de barras.
 * @param {Array} label - Array de labels para as barras do gráfico.
 * @returns {Object} - O gráfico de barras.
 */
export function drawBarChart(dataset, label) {
    const father = document.getElementById('expenses-bar-chart').getContext('2d');

    chart = new Chart(father, {
        type: 'bar',
        data: {
            labels: dataset.names,
            datasets: [
                {
                    label: label,
                    data: dataset.values,
                    backgroundColor: dataset.colors,
                },
            ],
        },
        options: {
            responsive: true,
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
                    text: label,
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
            onClick: handleBarClick,
            onHover: handleBarHover,
        },
    });

    return chart;
}

/**
 * Trata o evento do click. Se o evento é em uma das barras, atualiza o gráfico com as subcategorias. Se é fora das barras, volta ao gráfico inicial.
 * @param {Object} event - Recebe as informações passadas automaticamente pelo Char.js na função onClick.
 * @param {Array} elements - Recebe as propriedades específicas que são passadas automaticamente pelo Chart.js na função onClick
 */
function handleBarClick(event, elements) {
    if (chart && elements.length > 0) {
        const clickedIndex = elements[0].index,
            labelClicked = chart.data.labels[clickedIndex],
            barChartLevel = sessionStorage.getItem('bar_chart_level');

        sessionStorage.setItem('bar_label_clicked', labelClicked);

        if (barChartLevel == 'categories') {
            updateBarChart(chart);
        }
        sessionStorage.setItem('bar_chart_level', 'subcategories');
    } else {
        updateBarChart(chart);
        sessionStorage.setItem('bar_chart_level', 'categories');
    }
}

/**
 * Trata o evento do hover fazendo com que o cursor se torne pointer quando passa por uma das barras.
 * @param {Object} event - Recebe as informações passadas automaticamente pelo Char.js na função onClick.
 * @param {Array} elements - Recebe as propriedades específicas que são passadas automaticamente pelo Chart.js na função onClick
 */
function handleBarHover(event, elements) {
    if (chart) {
        chart.canvas.style.cursor = elements && elements.length > 0 ? 'pointer' : 'default';
    }
}

export function drawDoughnutChart(dataset, fatherHtmlId, label) {
    const father = document.getElementById(`${fatherHtmlId}-doughnut-chart`).getContext('2d');
    const data = {
        type: 'doughnut',
        data: {
            labels: dataset.names,
            backgroundColor: 'rgba(0, 0, 0, 1)',
            datasets: [
                {
                    label: label,
                    data: dataset.values,
                    backgroundColor: dataset.colors,
                    borderWidth: 4,
                    borderColor: 'rgba(50, 50, 50, 0.2)',
                    hoverOffset: 4,
                },
            ],
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: false,
                },
                title: {
                    display: true,
                    text: label,
                    font: {
                        size: 18,
                        family: 'Ubuntu',
                    },
                    color: 'rgba(204,204,204,1)',
                },
            },
        },
    };

    new Chart(father, data);
}

function addData(chart, label, data) {
    chart.data.labels.push(label);
    chart.data.datasets.forEach((dataset) => {
        dataset.data.push(data);
    });
    chart.update();
}

function removeData(chart) {
    chart.data.labels.pop();
    chart.data.datasets.forEach((dataset) => {
        dataset.data.pop();
    });
    chart.update();
}

export function updateChart(chart, dataset) {
    let max = chart.data.labels.length,
        i;

    for (i = 0; i < max; i++) {
        removeData(chart);
    }

    for (i = 0; i < dataset.names.length; i++) {
        addData(chart, dataset.names[i], dataset.values[i]);
    }
}
