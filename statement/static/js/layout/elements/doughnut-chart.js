export function drawDoughnutChart(dataset, label) {
    const father = document.getElementById('donnut-chart').getContext('2d');
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
                        size: 18,
                        family: 'Ubuntu'
                    },
                    color: 'rgba(204,204,204,1)'
                }
            }
        }
    }

    return new Chart(father, data);
}