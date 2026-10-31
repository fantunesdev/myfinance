(() => {
    const canvas = document.getElementById('investment-position-chart');
    const historyElement = document.getElementById('investment-position-history');
    if (!canvas || !historyElement || typeof Chart === 'undefined') return;

    const history = JSON.parse(historyElement.textContent);
    if (!history.dates.length) return;
    const points = history.dates.map((date, index) => ({
        x: new Date(`${date}T12:00:00`).getTime(),
        y: history.values[index],
    }));
    const singlePointPadding = points.length === 1 ? 12 * 60 * 60 * 1000 : 0;
    const currency = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
    const shortDate = new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit' });
    const fullDate = new Intl.DateTimeFormat('pt-BR');

    new Chart(canvas.getContext('2d'), {
        type: 'line',
        data: {
            datasets: [{
                label: 'Valor da posição',
                data: points,
                borderColor: 'rgba(46, 160, 110, 1)',
                backgroundColor: 'rgba(46, 160, 110, 0.12)',
                borderWidth: 2,
                pointRadius: 3,
                pointHoverRadius: 5,
                tension: 0,
                fill: true,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    type: 'linear',
                    min: points[0].x - singlePointPadding,
                    max: points[points.length - 1].x,
                    ticks: {
                        maxTicksLimit: 6,
                        callback: value => shortDate.format(value),
                    },
                },
                y: {
                    ticks: { callback: value => currency.format(value) },
                },
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        title: items => fullDate.format(items[0].parsed.x),
                        label: context => currency.format(context.parsed.y),
                    },
                },
            },
            animation: { duration: 200 },
        },
    });
})();
