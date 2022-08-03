import * as data from '../../data/graphics-data.js';
import { drawBarcode } from '../elements/graphics.js';

async function draw () {
    let year = data.getMonthYear().year,
        month = data.getMonthYear().month;
    
    let report = await data.groupByCategory(year, month),
        categoriesLists = data.getCategoriesLists(report.expenses);
    
    drawBarcode(categoriesLists, 'Gastos por Categoria');
}

draw()

