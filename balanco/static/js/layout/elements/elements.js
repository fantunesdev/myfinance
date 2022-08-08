function element(htmlId) {
    return document.querySelector(`#${htmlId}`)
}


export const expensesSelector = element('expenses-selector'),
    statementBox = element('statement-box'),
    originalTable = element('statement-table');