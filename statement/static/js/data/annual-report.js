import * as chartPolicy from './chart-policy.js';

export function setAnnualReport(transactions) {
    const revenues = {};
    const expenses = {};
    const investments = {};

    if (!transactions.length) {
        return {
            revenues: revenues,
            expenses: expenses,
            investments: investments,
        };
    }

    const years = transactions.map(t => Number(t.payment_date.split('-')[0]));
    const firstYear = Math.min(...years);
    const lastYear = Math.max(...years);

    for (let index = firstYear; index <= lastYear; index++) {
        revenues[index] = 0;
        expenses[index] = 0;
        investments[index] = 0;
    }

    for (const transaction of transactions) {
        if (!transaction.home_screen) continue;
        if (typeof transaction.card_number === 'object' && transaction.card_number && !transaction.card_number.home_screen) continue;

        const year = Number(transaction.payment_date.split('-')[0]);
        if (!chartPolicy.showInAnnualStatement(transaction)) continue;

        const isInvestment = transaction.type !== 'entrada' && chartPolicy.isInvestment(transaction);

        if (transaction.type == 'entrada') {
            revenues[year] += Number(transaction.value);
        } else {
            if (isInvestment) {
                investments[year] += Number(transaction.value);
            } else {
                expenses[year] += Number(transaction.value);
            }
        }
    }

    return {
        revenues: revenues,
        expenses: expenses,
        investments: investments,
    };
}

export function setAnnualDataset(report) {
    let names = [],
        values = [],
        colors = [],
        key;

    for (key in report) {
        names.push(key);
        values.push(report[key]);
        colors.push(`rgba(139, 0, 0, 1)`);
    }
    return { names, values, colors };
}
