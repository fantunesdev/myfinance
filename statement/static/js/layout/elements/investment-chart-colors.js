// Shared order and palette for patrimony and allocation, darkest to lightest.
export const investmentChartCategories = Object.freeze([
    { code: 'fixed_income', label: 'Renda fixa', color: 'rgba(110, 0, 0, 1)' },
    { code: 'variable_income', label: 'Renda variável', color: 'rgba(155, 0, 0, 1)' },
    { code: 'crypto', label: 'Cripto', color: 'rgba(200, 0, 0, 1)' },
    { code: 'international', label: 'Exterior', color: 'rgba(235, 30, 30, 1)' },
    { code: 'currency', label: 'Moeda', color: 'rgba(245, 70, 70, 1)' },
    { code: 'other', label: 'Outro', color: 'rgba(255, 110, 110, 1)' },
]);

export function progressionWithInvestmentColors(datasets) {
    const category = dataset => investmentChartCategories.find(item =>
        item.code === dataset.asset_type || item.label === dataset.label
    );
    const order = dataset => {
        const item = category(dataset);
        return item ? investmentChartCategories.indexOf(item) : investmentChartCategories.length;
    };
    return [...datasets].sort((left, right) => order(left) - order(right)).map(dataset => ({
        ...dataset,
        color: category(dataset)?.color || investmentChartCategories[0].color,
    }));
}

export function investmentRedGradient(index, count) {
    const start = [110, 0, 0];
    const end = [255, 110, 110];
    const fraction = index / Math.max(count - 1, 1);
    const channels = start.map((value, channel) => Math.round(value + (end[channel] - value) * fraction));
    return `rgba(${channels.join(', ')}, 1)`;
}
