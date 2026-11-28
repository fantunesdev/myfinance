export function drawStackedAreaChart(datasets, label, options = {}) {
    const father = document.getElementById('line-chart').getContext('2d');
    const money = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
    const shouldFillMobileChartHeight = window.matchMedia && window.matchMedia('(max-width: 600px)').matches;

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
                pointRadius: 0,
                pointHoverRadius: 4,
                pointHitRadius: 8,
                fill: true,
            })),
        },
        options: {
            responsive: true,
            maintainAspectRatio: options.maintainAspectRatio ?? !shouldFillMobileChartHeight,
            interaction: { mode: 'index', intersect: false },
            scales: {
                ...(options.xScale ? { x: options.xScale } : {}),
                y: {
                    stacked: true, // Ativa o empilhamento
                    beginAtZero: true,
                    min: options.yMin,
                    ticks: { callback: value => money.format(value) },
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
                tooltip: {
                    callbacks: {
                        label: context => `${context.dataset.label}: ${money.format(context.parsed.y)}`,
                        footer: items => items.length
                            ? `Total visível: ${money.format(items.reduce((total, item) => total + item.parsed.y, 0))}`
                            : '',
                        afterBody: items => {
                            if (!items.length) return [];
                            const index = items[0].dataIndex;
                            const adjustment = datasets.reduce((total, dataset) => total + Number(dataset.valuation_adjustments?.[index] || 0), 0);
                            if (Math.abs(adjustment) < 0.005) return [];
                            const formatted = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(adjustment);
                            return [`Avaliação/reconciliação: ${formatted}`, 'Não representa novo aporte nem lucro realizado.'];
                        },
                    },
                },
            },
            animation: {
                duration: 200,
            },
        },
    });

    return chart;
}
