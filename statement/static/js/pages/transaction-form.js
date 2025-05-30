import { showHide } from './index.js';
import { buttons, divs, selects } from '../layout/elements/transaction-form-elements.js';
import * as data from '../data/transaction-form-data.js';
import * as general from '../layout/general.js';
import * as services from '../data/services.js';
import * as selectInput from '../layout/elements/selects.js';

/**
 * Mostra e oculta campos do formulário de acordo com o meio de pagamento selecionado.
 */
function selectPaymentMethod() {
    const paymentMethod = selects.paymentMethod.value;
    if (paymentMethod == 1) {
        divs.account.classList.add('toggled');
        divs.card.classList.remove('toggled');
        selects.account.selectedIndex = 0;
    } else {
        divs.card.classList.add('toggled');
        divs.account.classList.remove('toggled');
        selects.card.selectedIndex = 0;
    }
}

/**
 * Altera a dada de efetivação de acordo com o meio de pagamento e a data do lançamento.
 */
async function changePaymentDateInput() {
    if (selects.paymentMethod.value == 1) {
        let cardId = selects.card.value;
        var card = await services.getSpecificResource('cards', cardId);
    }
    const releaseDate = selects.releaseDate.value,
        paymentDate = data.setPaymentDate(releaseDate, card);
    selects.paymentDate.value = paymentDate;
}

/**
 * Autogerencia o input do payment method para se ajustar de acordo com o meio de pagamento.
 */
(function autoHandlePaymentMethod() {
    const accountValue = selects.account.value;

    if (accountValue > 0) {
        selects.paymentMethod.value = 2;
    }
})();

/**
 * Seta o valor inicial do input Valor como '0,00'.
 */
(function setInitialValueInput() {
    if (selects.value.value) {
        selects.value.value;
    } else {
        selects.value.value = '0.00';
    }
})();

async function changeSubcategoriesInput(categoryId) {
    const subcategories = await services.getChildrenResource('categories', 'subcategories', categoryId);

    selectInput.renderOptions(selects.subcategory, subcategories);
}

if (buttons.installment) {
    buttons.installment.addEventListener('click', () => showHide(divs.installment));
}
buttons.otherOptions.addEventListener('click', () => showHide(divs.otherOptions));

selects.paymentMethod.addEventListener('change', () => selectPaymentMethod());

selects.card.addEventListener('change', () => changePaymentDateInput());
selects.account.addEventListener('change', () => changePaymentDateInput());
selects.releaseDate.addEventListener('change', () => changePaymentDateInput());

selects.category.addEventListener('change', () => changeSubcategoriesInput(selects.category.value));
selects.subcategory.addEventListener('change', () => {
    if (selects.subcategory.value == 5) {
        general.toggle('div-fuel');
        selects.price.required = true;
        selects.km.required = true;

        selects.price.addEventListener('keyup', () => {
            selects.observation.value = returnFuelObservation();
        });
        selects.value.addEventListener('keyup', () => {
            selects.observation.value = returnFuelObservation();
        });
        selects.km.addEventListener('keyup', () => {
            selects.observation.value = returnFuelObservation();
        });
    }
});

selects.value.addEventListener('keyup', twoDigitFloatHandler);
selects.price.addEventListener('keyup', twoDigitFloatHandler);

const divFuelToggler = document.querySelector('#div-fuel-toggler');
divFuelToggler.addEventListener('click', () => {
    general.toggle('div-fuel');
    selects.subcategory.value = 0;
    selects.price.required = false;
    selects.km.required = false;
});

function returnFuelObservation() {
    let price = selects.price.value,
        km = selects.km.value,
        value = selects.value.value,
        liters = (value / price).toFixed(2),
        kmPerL = (km / liters).toFixed(1),
        realPerKm = (value / km).toFixed(2);

    return `##########  CÁLCULOS DE COMBUSTÍVEL ##########

CUSTO: R$ ${realPerKm} por km.
CONSUMO: ${kmPerL} km/l.

PREÇO: R$ ${price}.
LITROS: ${liters} l.
DISTÂNCIA: ${km} km.

#########################################
`;
}

/**
 * Trata o valor do campo Valor de forma que sempre retorne um float de dois dígitos.
 *
 * @param {object} event - KeyboardEvent que pega a tecla que foi digitada.
 */
function twoDigitFloatHandler(event) {
    let value = this.value,
        valueString = value.toString(),
        valueLength = valueString.length,
        integer,
        cents;

    if (this.valueString == 0) {
        this.value = '';
    }

    if (valueLength == 3) {
        if (valueString.includes('.')) {
            this.value = valueString.replace('.', '');
            this.value = `0.${this.value}`;
        } else {
            integer = valueString.slice(0, -2);
            cents = valueString.slice(-2);
            this.value = `${integer}.${cents}`;
        }
    } else if (valueLength >= 4) {
        valueString = valueString.replace('.', '');
        integer = parseInt(valueString.slice(0, -2));
        cents = valueString.slice(-2);
        this.value = `${integer}.${cents}`;
    } else {
        this.value = `0.0${this.value}`;
    }
}

selectPaymentMethod();
