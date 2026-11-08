function shouldFillMobileChartHeight() {
    return window.matchMedia && window.matchMedia('(max-width: 600px)').matches;
}

/**
 * Monta o gráfico de barras.
 * @param {Object} dataset - Objeto com as informações que serão usadas para montar o gráfico de barras.
 * @param {Array} label - Array de labels para as barras do gráfico.
 * @returns {Object} - O gráfico de barras.
 */
export function drawBarChart(dataset, label, onUpdate) {
    const father = document.getElementById('expenses-bar-chart').getContext('2d');

    return new Chart(father, {
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
            maintainAspectRatio: !shouldFillMobileChartHeight(),
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
            onClick: (event, elements, chart) => handleBarClick(event, elements, chart, onUpdate),
            onHover: handleBarHover,
        },
    });
}

/**
 * Trata o evento do click. Se o evento é em uma das barras, atualiza o gráfico com as subcategorias. Se é fora das barras, volta ao gráfico inicial.
 * @param {Object} event - Recebe as informações passadas automaticamente pelo Char.js na função onClick.
 * @param {Array} elements - Recebe as propriedades específicas que são passadas automaticamente pelo Chart.js na função onClick
 */
function handleBarClick(event, elements, chart, onUpdate) {
    if (!chart) return;
    if (elements.length > 0) {
        const clickedIndex = elements[0].index,
            labelClicked = chart.data.labels[clickedIndex],
            barChartLevel = sessionStorage.getItem('bar_chart_level');

        if (barChartLevel === 'categories') {
            sessionStorage.setItem('bar_label_clicked', labelClicked);
            sessionStorage.removeItem('bar_subcategory_clicked');
            sessionStorage.setItem('bar_chart_level', 'subcategories');
        } else {
            sessionStorage.setItem('bar_subcategory_clicked', labelClicked);
        }
        return onUpdate?.(chart);
    } else {
        sessionStorage.removeItem('bar_label_clicked');
        sessionStorage.removeItem('bar_subcategory_clicked');
        sessionStorage.setItem('bar_chart_level', 'categories');
        return onUpdate?.(chart);
    }
}

/**
 * Trata o evento do hover fazendo com que o cursor se torne pointer quando passa por uma das barras.
 * @param {Object} event - Recebe as informações passadas automaticamente pelo Char.js na função onClick.
 * @param {Array} elements - Recebe as propriedades específicas que são passadas automaticamente pelo Chart.js na função onClick
 */
function handleBarHover(event, elements, chart) {
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
            maintainAspectRatio: !shouldFillMobileChartHeight(),
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

export function updateChart(chart, dataset) {
    chart.data.labels = dataset.names;
    chart.data.datasets.forEach(current => {
        current.data = dataset.values;
        current.backgroundColor = dataset.colors;
    });
    chart.update();
}
