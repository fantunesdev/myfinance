/**
 * Renderiza a opção do select vazio.
 * 
 * @param {object} select - Um input html.
 */
function renderDefaultOption(select) {
    let option;

    option = document.createElement('option');
    option.value = 0;
    option.text = '---------';
    select.add(option, select.options[0]);
}


/**
 * Renderiza options a partir de uma lista de objetos literais.
 * 
 * @param {object} select - Um input html.
 * @param {Array} objectList - Um array de objetos literais. 
 */
export function renderOptions(select, objectList) {
    console.log(objectList);
    select.length = 0;
    renderDefaultOption(select);
    
    for (let object of objectList) {
        const option = document.createElement('option');
        option.value = object.id;
        option.text = object.description;
        select.add(option, select.options[object.id])
    }
}