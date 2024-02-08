import { showHide } from './index.js';
import { buttons, divs, selects } from '../layout/elements/transaction-form-elements.js';
import * as data from '../data/transaction-form-data.js';
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
        let cardId = selects.card.value
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
    const subcategories = await services.getRelatedResource('categories', 'subcategories', categoryId);

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

selects.value.addEventListener('keyup', 
    /**
     * Trata o valor do campo Valor de forma que sempre retorne um float de dois dígitos.
     * 
     * @param {object} event - KeyboardEvent que pega a tecla que foi digitada.
     */
    function(event) {
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

  });

selectPaymentMethod();

