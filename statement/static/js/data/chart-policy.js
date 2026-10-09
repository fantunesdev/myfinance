const DEFAULT_FLAG_VALUE = true;

export function showInMonthlyCashflowDonut(transaction) {
    return getSubcategoryFlag(transaction, 'show_in_monthly_cashflow_donut');
}

export function showInAnnualStatement(transaction) {
    return getSubcategoryFlag(transaction, 'show_in_annual_statement');
}

export function showInMonthlyExpenseCategoryBar(transaction) {
    return getSubcategoryFlag(transaction, 'show_in_monthly_expense_category_bar');
}

export function showInAnnualExpenseCategoryBar(transaction) {
    return getSubcategoryFlag(transaction, 'show_in_annual_expense_category_bar');
}

export function showInMonthlyExpenseLine(transaction) {
    return getSubcategoryFlag(transaction, 'show_in_monthly_expense_line');
}

export function isInvestment(transaction) {
    if (transaction.subcategory_is_investment !== undefined) {
        return Boolean(transaction.subcategory_is_investment);
    }

    const subcategory = getTransactionSubcategory(transaction);
    return Boolean(subcategory && subcategory.is_investment);
}

function getSubcategoryFlag(transaction, flagName) {
    const transactionFlagName = `subcategory_${flagName}`;

    if (transaction[transactionFlagName] !== undefined) {
        return Boolean(transaction[transactionFlagName]);
    }

    const subcategory = getTransactionSubcategory(transaction);
    if (subcategory && subcategory[flagName] !== undefined) {
        return Boolean(subcategory[flagName]);
    }

    return DEFAULT_FLAG_VALUE;
}

function getTransactionSubcategory(transaction) {
    if (typeof transaction.subcategory === 'object' && transaction.subcategory !== null) {
        return transaction.subcategory;
    }

    return getSubcategoryById(transaction.subcategory);
}

function getSubcategoryById(subcategoryId) {
    const subcategories = [
        ...getSessionArray('subcategories'),
        ...getSessionArray('annual_subcategories'),
    ];

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
