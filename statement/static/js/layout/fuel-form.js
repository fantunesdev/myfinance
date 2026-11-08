import { calculateFuel, calculateOdometerInterval, resolveFuelInputs } from '../data/fuel-calculations.js';

export function initializeFuelForm() {
    const section = document.getElementById('div-fuel');
    if (!section) return;
    const field = name => document.getElementById(`id_${name}`);
    const history = JSON.parse(document.getElementById('fuel-history').textContent);
    const preview = document.getElementById('fuel-preview');
    const format = (value, digits = 2) => value === null ? 'Dados insuficientes' :
        value.toLocaleString('pt-BR', { minimumFractionDigits: digits, maximumFractionDigits: digits });
    function update(event) {
        const active = section.dataset.existing === 'true' ||
            (section.dataset.subcategory && field('subcategory').value === section.dataset.subcategory);
        section.classList.toggle('toggled', !active);
        if (!active) return;
        if (field('fuel_remove')?.checked) {
            preview.textContent = 'Os dados de abastecimento serão removidos ao salvar.';
            return;
        }
        const amount = field('fuel_amount_paid')?.value || field('value').value;
        const basis = field('fuel_calculation_basis');
        if (event?.target === field('fuel_price_per_liter')) basis.value = 'price';
        if (event?.target === field('fuel_liters')) basis.value = 'liters';
        const resolved = resolveFuelInputs({
            amount, liters: field('fuel_liters').value,
            price: field('fuel_price_per_liter').value, basis: basis.value,
        });
        field('fuel_price_per_liter').value = resolved.price;
        field('fuel_liters').value = resolved.liters;
        const liters = field('fuel_liters').value;
        const distance = field('fuel_distance_km').value;
        const currency = field('currency')?.value || 'BRL';
        const manual = calculateFuel({ amount, liters, distance });
        const current = {
            id: section.dataset.transaction,
            date: field('posted_date').value,
            liters, amount, currency,
            odometer: field('fuel_odometer_km').value,
            full_tank: field('fuel_full_tank').value === 'True',
            break_before: field('fuel_break_before').checked,
        };
        const interval = calculateOdometerInterval(history, current);
        const lines = [
            `Preço efetivo por litro (${currency}): ${format(Number(resolved.price) || null)}`,
            `Consumo pela distância informada (km/l): ${format(manual.consumption)}`,
            `Custo pela distância informada (${currency}/km): ${format(manual.cost)}`,
        ];
        if (basis.value === 'price' && liters) {
            lines.push(`Litros calculados pelo valor pago e preço por litro: ${format(Number(liters), 3)} l.`);
        }
        if (interval) {
            lines.push(`Consumo pelo hodômetro (km/l): ${format(interval.consumption)} — ${format(interval.distance, 1)} km / ${format(interval.liters, 3)} l`);
            lines.push(`Custo do intervalo (${currency}/km): ${format(interval.cost)}`);
            if (distance && Math.abs(Number(distance) - interval.distance) >= 0.1) {
                lines.push(`A distância informada difere em ${format(Math.abs(Number(distance) - interval.distance), 1)} km do intervalo pelo hodômetro. Em intervalos com abastecimentos parciais, as distâncias podem se referir a trechos diferentes.`);
            }
        } else {
            lines.push('Consumo pelo hodômetro: aguardando um intervalo entre tanques cheios com hodômetro e todos os litros registrados.');
        }
        if (field('fuel_full_tank').value !== 'True') {
            lines.push('Abastecimento parcial ou tanque não informado: o cálculo pela distância é uma estimativa; o consumo por intervalo aguarda o próximo tanque cheio.');
        }
        preview.replaceChildren(...lines.map(line => {
            const paragraph = document.createElement('p');
            paragraph.textContent = line;
            return paragraph;
        }));
    }
    for (const name of ['subcategory', 'value', 'currency', 'posted_date', 'fuel_amount_paid', 'fuel_liters', 'fuel_price_per_liter',
        'fuel_distance_km', 'fuel_odometer_km', 'fuel_full_tank', 'fuel_break_before', 'fuel_remove']) {
        for (const event of ['input', 'change', 'keyup']) field(name)?.addEventListener(event, update);
    }
    for (const name of ['category', 'type']) field(name)?.addEventListener('change', update);
    update();
}
