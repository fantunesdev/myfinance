function renderDefaultOption(input) {
    let option;

    option = document.createElement('option');
    option.value = 0;
    option.text = '---------';
    input.add(option, input.options[0]);
}

export function renderOptions(input, objectList) {
    input.length = 0;
    renderDefaultOption(input);
    
    for (let object of objectList) {
        const option = document.createElement('option');
        option.value = object.id;
        option.text = object.descricao;
        input.add(option, input.options[object.id])
    }
}