/**
 * Adiciona a classe CSS toggled para colapçar/mostrar elementos.
 *
 * @param {string} id - Uma string com o ID HTML do elemento que será colapsado/mostrado.
 */
export function toggle(id) {
    let box = document.getElementById(id);

    if (hasToggled(box.classList)) {
        box.classList.remove('toggled');
    } else {
        box.classList.add('toggled');
    }
}

/**
 * Verifica e inclui a classe CSS active na lista de classes de um elemento html.
 *
 * @param {Array} classList - Um array com as classes CSS de um elemento.
 * @returns - O array com as classes CSS com a classe active adicionada.
 */
export function hasToggled(classList) {
    let list = Array.from(classList);

    return list.includes('toggled');
}
