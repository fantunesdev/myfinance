import { showHide } from './index.js';
import { buttons, divs, selects } from '../layout/elements/transaction-form-elements.js';
import * as data from '../data/transaction-form-data.js';
import * as services from '../data/services.js';


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
    };
};


async function changePaymentDateInput() {
    if (selects.paymentMethod.value == 1) {
        let cardId = selects.card.value
        var card = await services.getSpecificResource('cards', cardId);
    };
    const releaseDate = selects.releaseDate.value,
        paymentDate = data.setPaymentDate(releaseDate, card);
    selects.paymentDate.value = paymentDate;
};

(function autoHandlePaymentMethod() {
    const accountValue = selects.account.value;

    if (accountValue > 0) {
        selects.paymentMethod.value = 2;
    }
})()


async function changeSubcategoriesInput(categoryId) {
    const subcategories = await services.getRelatedResource('categories', 'subcategories', categoryId);
}


if (buttons.installment) {
    buttons.installment.addEventListener('click', () => showHide(divs.installment));
};
buttons.otherOptions.addEventListener('click', () => showHide(divs.otherOptions));

selects.paymentMethod.addEventListener('change', () => selectPaymentMethod());

selects.card.addEventListener('change', () => changePaymentDateInput());
selects.account.addEventListener('change', () => changePaymentDateInput());
selects.releaseDate.addEventListener('change', () => changePaymentDateInput());

selects.category.addEventListener('change', () => changeSubcategoriesInput(selects.category.value));

selectPaymentMethod();

