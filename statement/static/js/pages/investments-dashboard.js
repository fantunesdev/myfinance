import * as stackedAreaChart from '../layout/elements/staked-area-chart.js';
import * as doughnutChart from '../layout/elements/doughnut-chart.js';

const datasetsElement = document.getElementById('investment-progression-datasets');
const datasets = datasetsElement ? JSON.parse(datasetsElement.textContent) : [];
const interestDatasetsElement = document.getElementById('investment-interest-datasets');
const interestDatasets = interestDatasetsElement ? JSON.parse(interestDatasetsElement.textContent) : [];
const chartToggle = document.getElementById('investment-chart-toggle');

let activeChart = 'progression';

function destroyInvestmentChart() {
    if (window.investmentChart) {
        window.investmentChart.destroy();
        window.investmentChart = null;
    }
}

function setChartToggleMode(mode) {
    if (!chartToggle) return;

    if (mode === 'interest') {
        chartToggle.innerHTML = '<i class="fa-solid fa-chart-area"></i>';
        chartToggle.setAttribute('title', 'Evolução patrimonial');
        chartToggle.setAttribute('aria-label', 'Evolução patrimonial');
        return;
    }

    chartToggle.innerHTML = '<i class="fa-solid fa-percent"></i>';
    chartToggle.setAttribute('title', 'Ganhos');
    chartToggle.setAttribute('aria-label', 'Ganhos');
}

function drawProgressionChart() {
    destroyInvestmentChart();
    activeChart = 'progression';
    setChartToggleMode('progression');

    if (!datasets.length || !datasets[0].names.length) return;

    window.investmentChart = stackedAreaChart.drawStackedAreaChart(
        datasets,
        'Evolução Patrimonial',
        { maintainAspectRatio: false, yMin: 0 }
    );
}

function drawInterestChart() {
    destroyInvestmentChart();
    activeChart = 'interest';
    setChartToggleMode('interest');

    if (!interestDatasets.length || !interestDatasets[0].names.length) return;

    const canvas = document.getElementById('line-chart');
    const formatter = new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL',
    });

    window.investmentChart = new Chart(canvas.getContext('2d'), {
        type: 'line',
        data: {
            labels: interestDatasets[0].names,
            datasets: interestDatasets.map((dataset) => ({
                label: dataset.label,
                data: dataset.values,
                borderColor: dataset.color,
                backgroundColor: dataset.color.replace('1)', '0.16)'),
                borderWidth: 2,
                pointRadius: 4,
                tension: 0.2,
                fill: dataset.label === 'Resultado',
            })),
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    ticks: {
                        callback: (value) => formatter.format(value),
                    },
                },
            },
            plugins: {
                legend: {
                    display: true,
                },
                title: {
                    display: true,
                    text: 'Ganhos',
                    font: {
                        size: 18,
                        family: 'Ubuntu',
                    },
                    color: 'rgba(204,204,204,1)',
                },
                tooltip: {
                    callbacks: {
                        label: (context) => `${context.dataset.label}: ${formatter.format(context.parsed.y)}`,
                    },
                },
            },
            animation: {
                duration: 200,
            },
        },
    });
}

if (chartToggle) {
    chartToggle.addEventListener('click', () => {
        if (activeChart === 'distribution') return;
        if (activeChart === 'interest') {
            drawProgressionChart();
            return;
        }

        drawInterestChart();
    });

    chartToggle.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ' || event.key === 'Spacebar') {
            event.preventDefault();
            chartToggle.click();
        }
    });
}

function getAllocationData() {
    const dataElement = document.getElementById('investment-allocation-data');
    const allocation = dataElement ? JSON.parse(dataElement.textContent) : { positions: [] };
    const types = [
        { code: 'fixed_income', label: 'Renda fixa', color: 'rgba(139, 0, 0, 1)' },
        { code: 'variable_income', label: 'Renda variável', color: 'rgba(190, 0, 0, 1)' },
    ];
    const selectedType = types.find(type => type.code === allocation.selected_type);
    const positions = allocation.positions || [];
    const entries = selectedType
        ? positions.filter(position => position.asset_type === selectedType.code)
        : types.map(type => ({
            label: type.label,
            value: positions.filter(position => position.asset_type === type.code)
                .reduce((sum, position) => sum + Number(position.value), 0),
        }));
    const labels = entries.map(entry => entry.label);
    const values = entries.map(entry => Math.max(0, Number(entry.value) || 0));
    const colors = selectedType
        ? entries.map((entry, index) => `rgba(${Math.round(110 + 80 * index / Math.max(entries.length - 1, 1))}, 0, 0, 1)`)
        : types.map(type => type.color);
    const total = values.reduce((sum, value) => sum + value, 0);
    return { types, selectedType, entries, labels, values, colors, total };
}

function drawDistributionChart(data) {
    destroyInvestmentChart();
    activeChart = 'distribution';
    if (chartToggle) chartToggle.hidden = true;

    const canvas = document.getElementById('line-chart');
    if (!canvas) return;
    const currency = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
    const percentage = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 });
    canvas.setAttribute('aria-label', `Distribuição do patrimônio em ${data.selectedType.label}: ${data.labels.map((label, index) => `${label}: ${currency.format(data.values[index])}`).join('; ')}`);

    window.investmentChart = new Chart(canvas.getContext('2d'), {
        type: 'bar',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Valor da posição',
                data: data.values,
                backgroundColor: data.colors,
                borderColor: data.colors,
                borderWidth: 1,
                borderRadius: 3,
                maxBarThickness: 72,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { ticks: { maxRotation: 45, minRotation: 0 } },
                y: {
                    min: 0,
                    ticks: { callback: value => currency.format(value) },
                },
            },
            plugins: {
                legend: { display: false },
                title: {
                    display: true,
                    text: `Distribuição do patrimônio — ${data.selectedType.label}`,
                    font: { size: 18, family: 'Ubuntu' },
                    color: 'rgba(204,204,204,1)',
                },
                tooltip: {
                    callbacks: {
                        label: context => `${currency.format(context.parsed.y)} (${percentage.format(data.total ? context.parsed.y / data.total * 100 : 0)}%)`,
                    },
                },
            },
            onClick: (event, elements) => {
                const entry = elements.length ? data.entries[elements[0].index] : null;
                if (entry) window.location.assign(entry.url);
            },
            onHover: (event, elements, chart) => {
                chart.canvas.style.cursor = elements.length ? 'pointer' : 'default';
            },
            animation: { duration: 200 },
        },
    });
}

function drawAllocationChart(data) {
    const canvas = document.getElementById('investment-allocation-chart');
    if (!canvas) return;
    const { types, selectedType, entries, labels, values, colors, total } = data;
    if (!total) {
        document.getElementById('investment-allocation-container').hidden = true;
        const empty = document.getElementById('investment-allocation-empty');
        empty.textContent = selectedType
            ? 'Nenhum investimento com valor positivo nesta categoria.'
            : 'Sem saldo em renda fixa ou renda variável.';
        empty.hidden = false;
        return;
    }

    const currency = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
    const percentage = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 });
    canvas.setAttribute('aria-label', labels.map((label, index) =>
        `${label}: ${currency.format(values[index])}, ${percentage.format(values[index] / total * 100)}%`
    ).join('; '));

    window.investmentAllocationChart = doughnutChart.drawDoughnutChart(
        {
            names: labels,
            values,
            colors,
        },
        selectedType ? selectedType.label : 'Renda fixa / variável',
        null,
        {
            canvasId: 'investment-allocation-chart',
            maintainAspectRatio: false,
            onSliceClick: index => {
                if (selectedType) {
                    if (entries[index]) window.location.assign(entries[index].url);
                    return;
                }
                if (!types[index] || !values[index]) return;
                const url = new URL(window.location.href);
                url.searchParams.set('asset_type', types[index].code);
                url.hash = '';
                window.location.assign(url.toString());
            },
            onHover: (event, elements, chart) => {
                chart.canvas.style.cursor = elements.length ? 'pointer' : 'default';
            },
            tooltip: {
                callbacks: {
                    label: context => `${context.label}: ${currency.format(context.parsed)} (${percentage.format(context.parsed / total * 100)}%)`,
                },
            },
        }
    );
}

function returnToOverviewOnEmptyClick(container, chart) {
    if (!container || !chart) return;
    container.addEventListener('click', event => {
        if (event.target.closest?.('a, button, [role="button"]')) return;
        if (event.target === chart.canvas) {
            const elements = chart.getElementsAtEventForMode(event, 'nearest', { intersect: true }, true);
            if (elements.length) return;
        }
        const url = new URL(window.location.href);
        url.searchParams.delete('asset_type');
        url.hash = '';
        window.location.assign(url.toString());
    });
}

const allocationData = getAllocationData();
drawAllocationChart(allocationData);
if (allocationData.selectedType) {
    drawDistributionChart(allocationData);
    returnToOverviewOnEmptyClick(document.getElementById('line-chart')?.parentElement, window.investmentChart);
    returnToOverviewOnEmptyClick(document.getElementById('investment-allocation-container'), window.investmentAllocationChart);
} else {
    drawProgressionChart();
}
