export function drawStackedAreaChart(datasets, label) {
    const father = document.getElementById('line-chart').getContext('2d');

    const chart = new Chart(father, {
        type: 'line',
        data: {
            labels: datasets[0].names,
            datasets: datasets.map((ds) => ({
                label: ds.label,
                data: ds.values,
                backgroundColor: ds.color.replace('1)', '0.4)'), // Torna a área semi-transparente
                borderColor: ds.color,
                borderWidth: 2,
                pointRadius: 4,
                fill: true,
            })),
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    stacked: true, // Ativa o empilhamento
                    beginAtZero: true,
                },
            },
            plugins: {
                legend: {
                    display: true,
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
        },
    });

    return chart;
}
