function getReport() {
    const source = document.getElementById('fuel-report');
    return source ? JSON.parse(source.textContent) : null;
}

const format = (value, digits = 2) => value === null || value === undefined ? 'Dados insuficientes' :
    Number(value).toLocaleString('pt-BR', { minimumFractionDigits: digits, maximumFractionDigits: digits });
const dateLabel = value => value.split('-').reverse().join('/');

export function hideFuelDashboard() {
    const section = document.getElementById('fuel-dashboard');
    if (section) section.hidden = true;
}

export function showFuelDashboard(itemId, itemType) {
    const report = getReport();
    const section = document.getElementById('fuel-dashboard');
    if (!report || !section) return;
    const ids = itemType === 'categories' ? report.category_ids : report.subcategory_ids;
    section.hidden = !ids.includes(Number(itemId));
    if (section.hidden) return;
    const setText = (id, text) => { document.getElementById(id).textContent = text; };
    const currency = report.currency || '—';
    setText('fuel-report-range', report.start ?
        `Períodos válidos de ${dateLabel(report.start)} a ${dateLabel(report.end)}. A média histórica usa apenas o hodômetro e os litros, independentemente do ano selecionado no gráfico.` :
        'A média histórica aguarda um intervalo completo entre dois tanques cheios com hodômetro e todos os litros registrados. A distância informada é usada somente no consumo individual do abastecimento.');
    setText('fuel-consumption', `Consumo médio histórico (km/l): ${format(report.consumption)} — ver períodos`);
    setText('fuel-cost', `Custo por km (${currency}): ${format(report.cost_per_km)}`);
    setText('fuel-price', `Preço efetivo médio por litro (${currency}): ${format(report.price_per_liter, 3)}`);
    setText('fuel-distance', `Distância acompanhada: ${format(report.distance, 1)} km`);
    setText('fuel-report-status', report.periods.length === 1 ? '1 período válido usado na média histórica.' :
        `${report.periods.length} períodos válidos usados na média histórica.`);

    const row = values => {
        const tr = document.createElement('tr');
        for (const value of values) {
            const cell = document.createElement('td');
            cell.textContent = value;
            tr.append(cell);
        }
        return tr;
    };
    document.getElementById('fuel-periods-body').replaceChildren(...report.periods.map(period => row([
        `${dateLabel(period.start)} a ${dateLabel(period.end)} (${period.duration})`,
        format(period.distance, 1), format(period.liters, 3), format(period.consumption),
    ])));
    document.getElementById('fuel-periods-total').replaceChildren(...(report.periods.length ? [row([
        'Média histórica ponderada', format(report.distance, 1), format(report.liters, 3), format(report.consumption),
    ])] : []));
    if (!report.periods.length) {
        const empty = row(['Ainda não há intervalos completos pelo hodômetro para calcular a média histórica.']);
        empty.firstChild.colSpan = 4;
        document.getElementById('fuel-periods-body').replaceChildren(empty);
    }
    document.getElementById('fuel-consumption').onclick = () => document.getElementById('fuel-periods').showModal();
}
