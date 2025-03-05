export function drawDoughnutChart(dataset, label, onClickCallback, select) {
    const father = document.getElementById('donnut-chart').getContext('2d');
    const data = {
        type: 'doughnut',
        data: {
            labels: dataset.names,
            datasets: [{
                label: label,
                data: dataset.values,
                backgroundColor: dataset.colors,
                borderWidth: 4,
                borderColor: 'rgba(12, 12, 12, 0.2)',
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
            },
            onClick: (event, elements) => {
                if (elements.length > 0) {
                    const clickedIndex = elements[0].index;
                    let select = '';
                    if (clickedIndex === 0) {
                        select = 'expenses';
                    } else if (clickedIndex === 1) {
                        select = 'investments';
                    } else if (clickedIndex === 2) {
                        select = 'revenues';
                    }
                    onClickCallback(select); // Chame a função de callback passando o novo valor de select
                }
            }
        }
    };

    return new Chart(father, data);
}
