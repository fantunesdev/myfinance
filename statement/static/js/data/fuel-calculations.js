const number = value => value === null || value === undefined || value === '' ? null : Number(value);

export function resolveFuelInputs({ amount, liters, price, basis }) {
    const total = number(amount);
    if (basis === 'price') {
        const unitPrice = number(price);
        return { price, liters: total > 0 && unitPrice > 0 ? (total / unitPrice).toFixed(3) : '' };
    }
    const volume = number(liters);
    return { liters, price: total > 0 && volume > 0 ? (total / volume).toFixed(4) : '' };
}

export function calculateFuel({ amount, liters, distance }) {
    amount = number(amount);
    liters = number(liters);
    distance = number(distance);
    return {
        price: amount > 0 && liters > 0 ? amount / liters : null,
        consumption: distance > 0 && liters > 0 ? distance / liters : null,
        cost: amount > 0 && distance > 0 ? amount / distance : null,
    };
}

export function calculateOdometerInterval(history, current) {
    if (current.full_tank !== true || number(current.odometer) === null || current.break_before) return null;
    const key = entry => [entry.date, Number(entry.id || Number.MAX_SAFE_INTEGER)];
    const [date, id] = key(current);
    const previous = history.filter(entry => {
        const [entryDate, entryId] = key(entry);
        return entryDate < date || (entryDate === date && entryId < id);
    });
    let liters = number(current.liters);
    let amount = number(current.amount);
    let lastOdometer = number(current.odometer);
    let sameCurrency = true;
    if (!(liters > 0)) return null;
    for (let index = previous.length - 1; index >= 0; index--) {
        const entry = previous[index];
        const odometer = number(entry.odometer);
        if (odometer !== null && odometer >= lastOdometer) return null;
        if (odometer !== null) lastOdometer = odometer;
        if (entry.full_tank === true && odometer !== null) {
            const distance = number(current.odometer) - odometer;
            return { start: entry.date, distance, liters,
                consumption: distance / liters, cost: sameCurrency ? amount / distance : null };
        }
        if (entry.break_before || !(number(entry.liters) > 0)) return null;
        liters += number(entry.liters);
        amount += number(entry.amount);
        sameCurrency = sameCurrency && entry.currency === current.currency;
    }
    return null;
}
