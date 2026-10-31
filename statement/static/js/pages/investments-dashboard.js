import * as stackedAreaChart from '../layout/elements/staked-area-chart.js';
import * as doughnutChart from '../layout/elements/doughnut-chart.js';
import { createInvestmentStore, stateFromUrl, stateUrl, DEFAULT_STATE } from '../data/investments-store.js';

const config = JSON.parse(document.getElementById('investment-dashboard-config').textContent);
let storage;
try { storage = window.sessionStorage; } catch { /* Memory-only mode. */ }
const store = createInvestmentStore({ userId: config.userId, apiUrl: config.apiUrl, storage });
let state = store.setState(stateFromUrl(window.location.href, store.getState()));
let dashboard = null;
let datasets = [];
let interestDatasets = [];
let activeChart = 'progression';
const chartToggle = document.getElementById('investment-chart-toggle');
const money = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
const quantity = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 8 });
const smallUnitPrice = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 8, maximumFractionDigits: 8 });
const typeLabels = { fixed_income: 'Renda fixa', variable_income: 'Renda variável', crypto: 'Cripto', currency: 'Disponível para investimento', other: 'Outros' };

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

function yearlyTimeline(labels) {
    const year = value => String(value).match(/\d{4}/)?.[0] || String(value);
    return {
        afterBuildTicks: axis => {
            const seen = new Set();
            axis.ticks = axis.ticks.filter(tick => {
                const label = year(labels[tick.value]);
                if (seen.has(label)) return false;
                seen.add(label);
                return true;
            });
        },
        ticks: {
            autoSkip: true,
            maxTicksLimit: 10,
            minRotation: 0,
            maxRotation: 0,
            callback: value => year(labels[value]),
        },
    };
}

function drawProgressionChart() {
    destroyInvestmentChart();
    activeChart = 'progression';
    if (chartToggle) chartToggle.hidden = false;
    setChartToggleMode('progression');

    const investedDatasets = datasets.filter(dataset => dataset.label !== 'Moeda');
    if (!investedDatasets.length || !investedDatasets[0].names.length) return;

    window.investmentChart = stackedAreaChart.drawStackedAreaChart(
        investedDatasets,
        'Evolução Patrimonial',
        { maintainAspectRatio: false, yMin: 0, xScale: yearlyTimeline(investedDatasets[0].names) }
    );
}

function drawInterestChart() {
    destroyInvestmentChart();
    activeChart = 'interest';
    if (chartToggle) chartToggle.hidden = false;
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
                x: yearlyTimeline(interestDatasets[0].names),
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

function getAllocationData() {
    const allocation = { selected_type: state.assetType, positions: dashboard.positions.filter(position =>
        ['fixed_income', 'variable_income', 'crypto'].includes(position.asset_type) && Number(position.value) > 0
    ) };
    const types = [
        { code: 'fixed_income', label: 'Renda fixa', color: 'rgba(139, 0, 0, 1)' },
        { code: 'variable_income', label: 'Renda variável', color: 'rgba(190, 0, 0, 1)' },
        { code: 'crypto', label: 'Cripto', color: 'rgba(165, 0, 0, 1)' },
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
    if (window.investmentAllocationChart) {
        window.investmentAllocationChart.destroy();
        window.investmentAllocationChart = null;
    }
    document.getElementById('investment-allocation-container').hidden = !total;
    document.getElementById('investment-allocation-empty').hidden = !!total;
    if (!total) {
        document.getElementById('investment-allocation-container').hidden = true;
        const empty = document.getElementById('investment-allocation-empty');
        empty.textContent = selectedType
            ? 'Nenhum investimento com valor positivo nesta categoria.'
            : 'Sem saldo em renda fixa, renda variável ou cripto.';
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
        selectedType ? selectedType.label : 'Distribuição',
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
                changeState({ assetType: types[index].code });
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


function cell(row, text) {
    const td = document.createElement('td');
    td.textContent = text;
    row.appendChild(td);
    return td;
}

function renderPositionGroups(positions) {
    const container = document.getElementById('investment-positions-body');
    container.replaceChildren();
    const grouped = new Map();
    for (const position of positions) {
        if (!grouped.has(position.asset_type)) grouped.set(position.asset_type, []);
        grouped.get(position.asset_type).push(position);
    }
    const order = Object.keys(typeLabels);
    const groups = [...grouped].sort(([left], [right]) => order.indexOf(left) - order.indexOf(right));
    for (const [type, entries] of groups) {
        const details = document.createElement('details');
        details.className = 'investment-position-group';
        details.dataset.assetType = type;
        details.open = state.openPositionTypes.includes(type);
        const summary = document.createElement('summary');
        const label = document.createElement('span');
        label.className = 'investment-position-group-label';
        label.textContent = typeLabels[type] || entries[0].asset_type_label;
        summary.appendChild(label);
        const total = document.createElement('strong');
        total.textContent = money.format(entries.reduce((sum, position) => sum + Number(position.value), 0));
        summary.appendChild(total);
        details.appendChild(summary);

        const unitMetrics = ['variable_income', 'crypto'].includes(type);
        const columns = ['Investimento', 'Broker', ...(unitMetrics ? ['Quantidade', 'Preço médio'] : []), 'Valor'];
        const scroll = document.createElement('div');
        scroll.className = 'investment-table-scroll';
        const table = document.createElement('table');
        table.className = 'table';
        const head = document.createElement('thead');
        const heading = document.createElement('tr');
        for (const column of columns) {
            const th = document.createElement('th');
            th.scope = 'col';
            th.textContent = column;
            heading.appendChild(th);
        }
        head.appendChild(heading);
        table.appendChild(head);
        const body = document.createElement('tbody');
        for (const position of entries) {
            const row = document.createElement('tr');
            const link = document.createElement('a');
            link.href = position.url;
            link.textContent = position.label;
            cell(row, '').appendChild(link);
            cell(row, position.broker);
            if (unitMetrics) {
                cell(row, quantity.format(Number(position.quantity)));
                const price = Number(position.average_purchase_price);
                cell(row, position.average_purchase_price === null ? '—' : (price < 0.01 ? smallUnitPrice : money).format(price));
            }
            cell(row, money.format(Number(position.value)));
            body.appendChild(row);
        }
        table.appendChild(body);
        scroll.appendChild(table);
        details.appendChild(scroll);
        details.addEventListener('toggle', () => {
            // Ignore queued events from elements replaced by a refresh/filter.
            if (!container.contains(details)) return;
            const open = new Set(state.openPositionTypes);
            if (open.has(type) === details.open) return;
            if (details.open) open.add(type);
            else open.delete(type);
            state = store.setState({ ...state, openPositionTypes: [...open] });
            syncUrl(true);
        });
        container.appendChild(details);
    }
    if (!positions.length) {
        const empty = document.createElement('p');
        empty.textContent = state.showAllPositions ? 'Nenhum investimento nesta seleção.' : 'Nenhuma posição com valor maior que zero nesta seleção.';
        container.appendChild(empty);
    }
}

function renderTables() {
    const positions = dashboard.positions.filter(position =>
        state.showAllPositions || Number(position.value) > 0
    );
    renderPositionGroups(positions);
    const brokers = document.getElementById('investment-brokers-body');
    brokers.replaceChildren();
    for (const broker of dashboard.brokers.filter(item => state.showAllBrokers || Number(item.value) > 0)) {
        const row = document.createElement('tr');
        cell(row, broker.label);
        cell(row, money.format(Number(broker.value)));
        brokers.appendChild(row);
    }
    if (!brokers.children.length) {
        const row = document.createElement('tr');
        cell(row, state.showAllBrokers ? 'Nenhum broker cadastrado.' : 'Nenhum broker com valor maior que zero.').colSpan = 2;
        brokers.appendChild(row);
    }
    document.getElementById('investment-positions-title').textContent = 'Posições';
    document.getElementById('investment-positions-toggle').textContent = state.showAllPositions ? 'Valor > 0' : 'Ver todas';
    document.getElementById('investment-brokers-toggle').textContent = state.showAllBrokers ? 'Valor > 0' : 'Ver todos';
    document.getElementById('investment-overview').hidden = !state.assetType;
}

function renderMetrics() {
    const totals = dashboard.totals;
    document.getElementById('investment-total').textContent = money.format(Number(totals.total));
    const result = Number(totals.net_income);
    const resultValue = document.getElementById('investment-result');
    resultValue.textContent = money.format(result);
    resultValue.classList.toggle('green', result > 0);
    resultValue.classList.toggle('red', result < 0);
    document.getElementById('investment-result-label').textContent = result > 0 ? 'Lucro' : result < 0 ? 'Prejuízo' : 'Resultado';
    document.getElementById('investment-available').textContent = money.format(Number(totals.available_to_invest));
    document.getElementById('investment-available-card').classList.toggle('investment-card-available-positive', Number(totals.available_to_invest) > 0);
    document.getElementById('investment-create-wallet').hidden = dashboard.has_default_wallet;
}

function renderCharts() {
    const allocation = getAllocationData();
    drawAllocationChart(allocation);
    if (state.assetType) drawDistributionChart(allocation);
    else if (state.chartMode === 'interest') drawInterestChart();
    else drawProgressionChart();
}

function syncUrl(replace = false) {
    const url = stateUrl(window.location.href, state);
    const historyState = { ...window.history.state, investmentDashboard: state };
    window.history[replace ? 'replaceState' : 'pushState'](historyState, '', url);
    document.getElementById('investment-overview').href = stateUrl(url, { ...state, assetType: '' });
    document.getElementById('investment-positions-toggle').href = stateUrl(url, { ...state, showAllPositions: !state.showAllPositions });
    document.getElementById('investment-brokers-toggle').href = stateUrl(url, { ...state, showAllBrokers: !state.showAllBrokers });
}

function changeState(change, push = true) {
    const previous = state;
    const next = { ...state, ...change };
    if (push && change.assetType) {
        next.openPositionTypes = [change.assetType];
    }
    state = store.setState(next);
    if (push) syncUrl();
    else syncUrl(true);
    if (!dashboard) return;
    renderTables();
    if (previous.assetType !== state.assetType || previous.chartMode !== state.chartMode) renderCharts();
}

function message(text, error = false) {
    const element = document.getElementById('investment-load-status');
    element.textContent = text;
    element.hidden = !text;
    element.setAttribute('role', error ? 'alert' : 'status');
}

let refreshing = false;
async function refresh(force = false) {
    if (refreshing) return;
    refreshing = true;
    document.getElementById('investment-refresh').disabled = true;
    message(dashboard ? 'Atualizando investimentos…' : 'Carregando investimentos…');
    try {
        dashboard = await store.load({ force });
        datasets = dashboard.progression_datasets;
        interestDatasets = dashboard.interest_datasets;
        renderMetrics();
        renderTables();
        renderCharts();
        message('');
    } catch (error) {
        if (error.auth) {
            dashboard = null;
            destroyInvestmentChart();
            window.investmentAllocationChart?.destroy();
            window.investmentAllocationChart = null;
            for (const id of ['investment-total', 'investment-result', 'investment-available']) document.getElementById(id).textContent = '—';
            document.getElementById('investment-positions-body').replaceChildren();
            document.getElementById('investment-brokers-body').replaceChildren();
        }
        message(`${error.message}${dashboard ? ' Os valores exibidos são da última atualização.' : ''}`, true);
    } finally {
        refreshing = false;
        document.getElementById('investment-refresh').disabled = false;
    }
}

function overview(event) {
    event?.preventDefault();
    changeState({ assetType: '', openPositionTypes: [] });
}

document.getElementById('investment-overview').addEventListener('click', overview);
document.getElementById('investment-positions-toggle').addEventListener('click', event => {
    event.preventDefault();
    changeState({ showAllPositions: !state.showAllPositions });
});
document.getElementById('investment-brokers-toggle').addEventListener('click', event => {
    event.preventDefault();
    changeState({ showAllBrokers: !state.showAllBrokers });
});
chartToggle.addEventListener('click', () => {
    if (!state.assetType) changeState({ chartMode: state.chartMode === 'interest' ? 'progression' : 'interest' });
});
chartToggle.addEventListener('keydown', event => {
    if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); chartToggle.click(); }
});
for (const [container, getChart] of [
    [document.getElementById('line-chart').parentElement, () => window.investmentChart],
    [document.getElementById('investment-allocation-container'), () => window.investmentAllocationChart],
]) {
    container.addEventListener('click', event => {
        if ((!state.assetType && !state.openPositionTypes.length) || event.target.closest?.('a, button, [role="button"]')) return;
        const chart = getChart();
        if (chart && event.target === chart.canvas && chart.getElementsAtEventForMode(event, 'nearest', { intersect: true }, true).length) return;
        overview();
    });
}
window.addEventListener('popstate', event => {
    changeState(event.state?.investmentDashboard || stateFromUrl(window.location.href, DEFAULT_STATE), false);
});
document.getElementById('investment-refresh').addEventListener('click', () => refresh(true));
let refreshTimer;
window.addEventListener('investments:changed', event => {
    if (!store.invalidate(event.detail?.revision)) return;
    clearTimeout(refreshTimer);
    if (document.visibilityState !== 'hidden') refreshTimer = setTimeout(() => refresh(), 150);
});
function refreshIfNeeded() {
    if (document.visibilityState !== 'hidden' && !store.isFresh()) refresh();
}
document.addEventListener('visibilitychange', refreshIfNeeded);
window.addEventListener('pageshow', refreshIfNeeded);
syncUrl(true);
const existing = store.peek();
if (existing) {
    dashboard = existing;
    datasets = dashboard.progression_datasets;
    interestDatasets = dashboard.interest_datasets;
    renderMetrics(); renderTables(); renderCharts();
}
if (!store.isFresh()) refresh();
else message('');
