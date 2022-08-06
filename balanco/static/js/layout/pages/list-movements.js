import * as data from '../../data/categories-report.js';
import * as dataSubcategories from '../../data/subcategory-expenses.js';
import * as graphics from '../elements/graphics.js';
import * as selects from '../elements/selects.js';
import * as services from '../../data/services.js';


const selector = document.getElementById('bar-chart-select');

async function draw () {
    const [year, month] = await data.getMonthYear(),
        report = await data.setCategoriesReport(year, month),
        revenue = data.setCategoriesDataset(report.revenue, true),
        expenses = data.setCategoriesDataset(report.expenses),
        amount = data.setAmountDataset(report.amount),
        htmlId = 'bar-chart-select',
        optionsCategory = data.setCategoriesOptions(report.expenses);

    selects.renderOptions(htmlId, optionsCategory);

    const barChart = graphics.drawBarChart(expenses, 'Despesas');
    graphics.drawDoughnutChart(revenue, 'revenue', 'Receitas');
    graphics.drawDoughnutChart(amount, 'amount', 'Receitas/Despesas');    

    return barChart;
};


async function updateBarChart(barChart) {
    const [year, month] = await data.getMonthYear();
        
    if (selector.value === '0') {
        const report = await data.setCategoriesReport(year, month);
        var expenses = report.expenses;
    } else {
        var expenses = await dataSubcategories.setSubcategoryDataset(year, month, selector.value);
    }

    const dataset = data.setCategoriesDataset(expenses);
    graphics.updateChart(barChart, dataset);
};

async function updateTable() {
    const originalTalbe = document.getElementById('movements-table');

    if (selector.value === '0') {
        originalTalbe.classList.remove('toggled');
    } else {
        originalTalbe.classList.add('toggled');
    }
}
    
    
selector.addEventListener('change', () => {
    updateBarChart(barChart);
    // updateTable();
});

let barChart = await draw();