export const columnTitles = ['Data', 'Categoria', 'Sub-Categoria', 'Descricao', 'Valor', 'Ações'];


export function orderExpensesBySubcategory(movements, categoryId, expenses) {
    let newMovements = [];
    for (let i = 0; i < expenses.length; i++) {
        expenses[i].order = i;
    };

    for (let movement of movements) {
        if (movement.categoria == categoryId) {
            for (let expense of expenses) {
                if (movement.subcategoria == expense.id) {
                    movement.order = expense.order;
                }
            }
            newMovements.push(movement);
        };
    };

    return newMovements.sort((a, b) => a.order < b.order ? -1 : a.order > b.order ? 1 : 0);
};


export function setData(movement, subcategories, category) {
    let data = [];

    data.push(movement.data_lancamento.split('-').reverse().join('/'));
    data.push(category.descricao);
    for (let subcategory of subcategories) {
        if (movement.subcategoria == subcategory.id) {
            data.push(`${subcategory.name}`);
        }
    }
    data.push(movement.descricao);
    data.push(movement.valor.toLocaleString('pt-br',{style: 'currency', currency: movement.moeda}));
    return data;
};


export function setURLs(movement) {
    let urls = [];
    
    if (movement.parcelamento) {
        urls = [
            `/parcelamento/${movement.parcelamento}/`,
            `/parcelamento/editar/${movement.parcelamento}`,
            `/parcelamento/remover/${movement.parcelamento}`
        ]
    } else {
        urls = [
            `/movimentacao/${movement.id}/`,
            `/movimentacao/editar/${movement.id}`,
            `/movimentacao/remover/${movement.id}`
        ]
    }    
    return urls;
}