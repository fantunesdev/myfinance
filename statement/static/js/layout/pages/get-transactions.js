import * as categoryData from '../../data/categories-report.js';
import * as subcategoryData from '../../data/subcategory-expenses.js';
import * as dataTable from '../../data/expenses-table.js';
import * as graphics from '../elements/graphics.js';
import * as selects from '../elements/selects.js';
import * as tables from '../elements/tables.js';
import * as services from '../../data/services.js';
import { expensesSelector, originalTable, statementBox } from '../elements/elements.js';

async function draw() {
    const [year, month] = await categoryData.getMonthYear(),
        movements = await services.getMovementsYearMonth(year, month),
        report = await categoryData.setCategoriesReport(movements),
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
        movements = await services.getMovementsYearMonth(year, month);
        
    if (expensesSelector.value === '0') {
        const report = await categoryData.setCategoriesReport(movements);
        var expenses = report.expenses;
    } else {
        var expenses = await subcategoryData.setSubcategoryDataset(year, month, expensesSelector.value);
    }

    const dataset = categoryData.setCategoriesDataset(expenses);
    graphics.updateChart(barChart, dataset);

    updateTable(movements, expenses)
};

async function updateTable(movements, expenses) {
    let subcategoryTable = document.getElementById('subcategory-table');

    if (subcategoryTable) {
        subcategoryTable.parentNode.removeChild(subcategoryTable);
    }
    if (expensesSelector.value === '0') {
        originalTable.classList.remove('toggled');
    } else {
        const category = await services.getViewDetail('categorias', expensesSelector.value);

        originalTable.classList.add('toggled');
        let filteredMovements = dataTable.orderExpensesBySubcategory(movements, expensesSelector.value, expenses);

        tables.renderTable(statementBox, filteredMovements, expenses, category);
    }
}
    
    
expensesSelector.addEventListener('change', () => {
    updateBarChart(barChart);
});

let barChart = await draw();