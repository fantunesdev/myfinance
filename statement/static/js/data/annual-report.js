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
        const category = getCategory(transaction.category);

        if (transaction.type == 'entrada') {
            revenues[year] += Number(transaction.value);
        } else {
            if (isInvestmentTransaction(transaction)) {
                investments[year] += Number(transaction.value);
            } else {
                if (category && category.ignore) continue;
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

function getCategory(categoryId) {
    const categories = getSessionArray('categories');

    for (const category of categories) {
        if (category.id == categoryId) {
            return category;
        }
    }
}

function isInvestmentTransaction(transaction) {
    if (transaction.subcategory_is_investment !== undefined) {
        return Boolean(transaction.subcategory_is_investment);
    }

    const subcategory = getSubcategory(transaction.subcategory);
    return Boolean(subcategory && subcategory.is_investment);
}

function getSubcategory(subcategoryId) {
    const subcategories = getSessionArray('subcategories');

    for (const subcategory of subcategories) {
        if (subcategory.id == subcategoryId) {
            return subcategory;
        }
    }
}

function getSessionArray(key) {
    try {
        const data = JSON.parse(sessionStorage.getItem(key) || '[]');
        return Array.isArray(data) ? data : [];
    } catch (error) {
        return [];
    }
}
