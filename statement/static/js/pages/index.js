export function getElement(htmlId) {
    return document.querySelector(`#${htmlId}`);
}

export function showHide(element) {
    if (hasToggled(element.classList)) {
        element.classList.remove('toggled');
    } else {
        element.classList.add('toggled');
    }
}

function hasToggled(classList) {
    let list = Array.from(classList);

    return list.includes('toggled');
}
