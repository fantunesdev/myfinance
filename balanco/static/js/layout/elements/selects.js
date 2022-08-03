function renderDefaultOption(htmlId) {
    const father = document.getElementById(htmlId);
    let option;

    option = document.createElement('option');
    option.value = 0;
    option.text = '---------';
    father.add(option, father.options[0]);
}


export function renderOptions(htmlId, objectList) {
    const father = document.getElementById(htmlId);
    
    father.length = 0;
    renderDefaultOption(htmlId);
    
    for (let object of objectList) {
        const option = document.createElement('option');
        option.value = object.id;
        option.text = object.descricao;
        father.add(option, father.options[object.id])
    }
}