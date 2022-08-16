import { getElement } from "../../pages/index.js";


export const buttons = {
    installment: getElement('btn-installment'),
    otherOptions: getElement('btn-other-options')
};


export const divs = {
    account: getElement('div-account'),
    card: getElement('div-card'),
    installment: getElement('div-installment'),
    otherOptions: getElement('div-other-options')
};

export const selects = {
    paymentMethod: getElement('id_payment_method'),
    account: getElement('id_account'),
    card: getElement('id_card'),
    releaseDate: getElement('id_release_date'),
    paymentDate: getElement('id_payment_date'),
    category: getElement('id_category'),
    subcategory: getElement('id_subcategory')
};