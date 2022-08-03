import * as graphicsData from '../../data/graphics-data.js';

export async function drawBarcode(categories, label) {
    const father = document.getElementById('categories').getContext('2d'),
    chart = new Chart(father, {
        type: 'bar',
        data: {
            labels: categories.names,
            datasets: [{
                label: label,
                data: categories.values,
                backgroundColor: categories.colors
            }]
        },
        options: {
            scales: {
                y: {
                    beginZero: true
                }
            }
        }
    });
}