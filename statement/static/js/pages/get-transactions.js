import * as categoryData from '../data/categories-report.js';
import * as subcategoryData from '../data/subcategory-expenses.js';
import * as dataTable from '../data/expenses-table.js';
import * as graphics from '../layout/elements/graphics.js';
import * as selects from '../layout/elements/selects.js';
import * as tables from '../layout/elements/tables.js';
import * as services from '../data/services.js';
import { expensesSelector, originalTable, statementBox } from '../layout/elements/get-transactions-elements.js';

async function draw() {
    const [year, month] = await categoryData.getMonthYear(),
        transactions = await services.getTransactionsByYearAndMonth(year, month),
        report = await categoryData.setCategoriesReport(transactions),
        revenue = categoryData.setCategoriesDataset(report.revenue, true),
        expenses = categoryData.setCategoriesDataset(report.expenses),
        amount = categoryData.setAmountDataset(report.amount),
        optionsCategory = categoryData.setCategoriesOptions(report.expenses);

    selects.renderOptions(expensesSelector, optionsCategory);

    const barChart = graphics.drawBarChart(expenses, 'Despesas');
    graphics.drawDoughnutChart(revenue, 'revenue', 'Receitas');
    graphics.drawDoughnutChart(amount, 'amount', 'Receitas/Despesas');    

    return barChart;
};


async function updateBarChart(barChart) {
    const [year, month] = await categoryData.getMonthYear(),
        transactions = await services.getTransactionsByYearAndMonth(year, month);
        
    if (expensesSelector.value === '0') {
        const report = await categoryData.setCategoriesReport(transactions);
        var expenses = report.expenses;
    } else {
        var expenses = await subcategoryData.setSubcategoryDataset(year, month, expensesSelector.value);
    }

    const dataset = categoryData.setCategoriesDataset(expenses);
    graphics.updateChart(barChart, dataset);

    updateTable(transactions, expenses)
};


async function updateTable(transactions, expenses) {
    let subcategoryTable = document.getElementById('subcategory-table');

    if (subcategoryTable) {
        subcategoryTable.parentNode.removeChild(subcategoryTable);
    }
    if (expensesSelector.value === '0') {
        originalTable.classList.remove('toggled');
    } else {
        const category = await services.getSpecificResource('categories', expensesSelector.value),
            accounts = await services.getResource('accounts'),
            cards = await services.getResource('cards'),
            banks = await services.getResource('banks'),
            transactionAttrs = {
                accounts: accounts,
                cards: cards,
                category: category,
                subcategories: expenses,
                banks: banks
            };


        originalTable.classList.add('toggled');
        let filteredTransactions = dataTable.orderExpensesBySubcategory(transactions, expensesSelector.value, expenses);

        tables.renderTable(statementBox, filteredTransactions, transactionAttrs);
    }
}
    
    
expensesSelector.addEventListener('change', () => {
    updateBarChart(barChart);
});

let barChart = await draw();