import * as data from '../../data/categories-report.js';
import * as dataSubcategories from '../../data/subcategory-expenses.js';
import * as graphics from '../elements/graphics.js';
import * as selects from '../elements/selects.js';
import * as services from '../../data/services.js';


const selector = document.getElementById('bar-chart-select');

async function draw () {
    const year = data.getMonthYear().year,
        month = data.getMonthYear().month,
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
    const  year = data.getMonthYear().year,
        month = data.getMonthYear().month;
        
    if (selector.value === '0') {
        const report = await data.setCategoriesReport(year, month);
        var expenses = report.expenses;
    } else {
        var expenses = await dataSubcategories.setSubcategoryDataset(year, month, selector.value);
    }

    const dataset = data.setCategoriesDataset(expenses);
    graphics.updateChart(barChart, dataset);
};
    
    
selector.addEventListener('change', () => {
    updateBarChart(barChart);
});

let barChart = await draw();