import * as data from '../../data/categories-report.js';
import * as dataSubcategories from '../../data/subcategory-expenses.js';
import * as graphics from '../elements/graphics.js';
import * as selects from '../elements/selects.js';
import * as services from '../../data/services.js';


const selector = document.getElementById('bar-chart-select');

async function draw () {
    const year = data.getMonthYear().year,
        month = data.getMonthYear().month;
    
    let report = await data.setCategoriesReport(year, month),
        revenue = data.setCategoriesDataset(report.revenue, true),
        expenses = data.setCategoriesDataset(report.expenses),
        amount = data.setAmountDataset(report.amount),
        htmlId = 'bar-chart-select',
        categories = await services.getView('categorias');
    
    const barChart = await graphics.drawBarChart(expenses, 'Gastos por Categoria');
    graphics.drawDoughnutChart(revenue, 'revenue', 'Receitas');
    graphics.drawDoughnutChart(amount, 'amount', 'Saídas/Entradas');

    selects.renderOptions(htmlId, categories);

    return barChart;
};


async function drawSubcategories() {
    const  year = data.getMonthYear().year,
        month = data.getMonthYear().month,
        subcategories = await services.getRelatedView('categorias', 'subcategorias', selector.value),
        expenses = await dataSubcategories.setSubcategoryExpenses(year, month, selector.value),
        dataset = data.setCategoriesDataset(expenses);
    barChart.destroy();
    return graphics.drawBarChart(dataset, `Gastos por Subcategoria`);
};


selector.addEventListener('change', () => {
    let barChart = drawSubcategories();
});

let barChart = await draw();