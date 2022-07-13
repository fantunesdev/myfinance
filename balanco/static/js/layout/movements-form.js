import * as scripts from './scripts.js'

function element(htmlId) {
    return document.querySelector(`#${htmlId}`)
}

function showHide(element) {
    if (hasToggled(element.classList)) {
        element.classList.remove('toggled')
    } else {
        element.classList.add('toggled')
    }
}

function hasToggled(classList) {
    let list = Array.from(classList);

    return list.includes('toggled');
}

const buttons = {
    installment: element('btn-installment'),
    otherOptions: element('btn-other-options')
}

const divs = {
    installment: element('div-installment'),
    otherOptions: element('div-other-options')
}

if (buttons.installment) {
    buttons.installment.addEventListener('click', () => showHide(divs.installment));
}
buttons.otherOptions.addEventListener('click', () => showHide(divs.otherOptions));