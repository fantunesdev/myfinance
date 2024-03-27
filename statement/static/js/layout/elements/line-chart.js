let chart;

/**
 * Monta o gráfico de linhas.
 * @param {Object} dataset - Objeto com as informações que serão usadas para montar o gráfico.
 * @param {Array} label - Array de labels para as barras do gráfico.
 * @returns {Object} - O gráfico.
 */
export function drawLineChart(dataset, label) {
    const father = document.getElementById('line-chart').getContext('2d');

    chart = new Chart(father, {
        type: 'line',
        data: {
            labels: dataset.names,
            datasets: [{
                label: label,
                data: dataset.values,
                backgroundColor: dataset.colors,
                borderColor: 'rgba(139, 0, 0, 1)',
                borderWidth: 4,
                pointRadius: 6
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
                        size: 18,
                        family: 'Ubuntu'
                    },
                    color: 'rgba(204,204,204,1)'
                }
            },
            animation: {
                duration: 200,
            }
        }
    });

    return chart;
}