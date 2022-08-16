function renderDefaultOption(select) {
    let option;

    option = document.createElement('option');
    option.value = 0;
    option.text = '---------';
    select.add(option, select.options[0]);
}


export function renderOptions(select, objectList) {    
    select.length = 0;
    renderDefaultOption(select);
    
    for (let object of objectList) {
        const option = document.createElement('option');
        option.value = object.id;
        option.text = object.description;
        select.add(option, select.options[object.id])
    }
}