import * as services from './services.js';


export async function setSubcategoryDataset(year, month, id) {
    const movements = await services.getMovementsYearMonth(year, month),
        subcategories = await services.getRelatedResource('categorias','subcategorias', id);

    let expenses = [],
        subcategory, movement, object;

    for (subcategory of subcategories) {
        object = {
            id: subcategory.id,
            name: subcategory.descricao,
            amount: 0
        }
        expenses.push(object);
    };

    for (movement of movements) {
        for (subcategory of expenses) {
            if (subcategory.id === movement.subcategoria) {
                subcategory.amount += movement.valor;
            }
        }
    };

    expenses.sort((a, b) => a.amount < b.amount ? 1 : a.amount > b.amount ? -1 : 0);

    return expenses;
};