import { showHide } from './index.js';
import { buttons, divs, selects } from '../layout/elements/transaction-form-elements.js';
import * as data from '../data/transaction-form-data.js';
import * as general from '../layout/general.js';
import * as services from '../data/services.js';
import * as selectInput from '../layout/elements/selects.js';

/**
 * Cache para dados de home_screen na sessão
 * Evita chamadas repetidas à API
 */
const homeScreenCache = {
    cards: {},
    cardNumbers: {},
    accounts: {},
    
    getKey(type, id) {
        return `homescreen_${type}_${id}`;
    },
    
    get(type, id) {
        const key = this.getKey(type, id);
        const cached = sessionStorage.getItem(key);
        return cached !== null ? JSON.parse(cached) : null;
    },
    
    set(type, id, value) {
        const key = this.getKey(type, id);
        sessionStorage.setItem(key, JSON.stringify(value));
    }
};

/**
 * Busca dados de home_screen da API com cache
 */
async function fetchHomeScreenValue(resourceType, resourceId) {
    if (!resourceId) return false;
    
    // Verificar cache primeiro
    const cached = homeScreenCache.get(resourceType, resourceId);
    if (cached !== null) {
        return cached;
    }
    
    try {
        const resource = await services.getSpecificResource(resourceType, resourceId);
        const homeScreenValue = resource && resource.home_screen ? resource.home_screen : false;
        homeScreenCache.set(resourceType, resourceId, homeScreenValue);
        return homeScreenValue;
    } catch (e) {
        console.error(`Erro ao buscar home_screen para ${resourceType} ${resourceId}:`, e);
        return false;
    }
}

/**
 * Atualiza o checkbox de home_screen baseado na seleção de account/card/card_number
 */
async function updateHomeScreenCheckbox() {
    const homeScreenCheckbox = document.getElementById('id_home_screen');
    if (!homeScreenCheckbox) return;
    
    const accountSelect = document.getElementById('id_account');
    const cardSelect = document.getElementById('id_card');
    const cardNumberSelect = document.getElementById('id_card_number');
    
    let homeScreenValue = false;
    
    // Verificar card_number primeiro (se selecionado e visible)
    if (cardNumberSelect && cardNumberSelect.offsetParent !== null) {
        const cardNumberId = cardNumberSelect.value;
        if (cardNumberId) {
            homeScreenValue = await fetchHomeScreenValue('card-numbers', cardNumberId);
            homeScreenCheckbox.checked = homeScreenValue;
            return;
        }
    }
    
    // Depois verificar card
    if (cardSelect) {
        const cardId = cardSelect.value;
        if (cardId) {
            homeScreenValue = await fetchHomeScreenValue('cards', cardId);
            homeScreenCheckbox.checked = homeScreenValue;
            return;
        }
    }
    
    // Por fim, verificar account
    if (accountSelect) {
        const accountId = accountSelect.value;
        if (accountId) {
            homeScreenValue = await fetchHomeScreenValue('accounts', accountId);
            homeScreenCheckbox.checked = homeScreenValue;
            return;
        }
    }
    
    // Se nada foi selecionado, desmarcar
    homeScreenCheckbox.checked = false;
}

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
    // Atualizar home_screen quando muda o payment method
    updateHomeScreenCheckbox();
}

/**
 * Altera a dada de efetivação de acordo com o meio de pagamento e a data do lançamento.
 */
async function changePaymentDateInput() {
    if (selects.paymentMethod.value == 1) {
        let cardId = selects.card.value;
        var card = await services.getSpecificResource('cards', cardId);
    }
    const releaseDate = selects.postedDate ? selects.postedDate.value : selects.releaseDate.value,
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

if (selects.postedDate) selects.postedDate.addEventListener('change', () => changePaymentDateInput());
else if (selects.releaseDate) selects.releaseDate.addEventListener('change', () => changePaymentDateInput());

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

// Popula o select de números de cartão com base no cartão selecionado usando dados injetados no template
async function populateCardNumbersForCard(cardId) {
    const select = document.getElementById('id_card_number');
    const wrapper = document.getElementById('div-card-number');

    // card_numbers_json pode ser injetado como um array JS (objeto) ou como uma string JSON.
    const raw = window.card_numbers_json || '[]';
    let cardNumbers = [];
    if (typeof raw === 'string') {
        try {
            cardNumbers = JSON.parse(raw);
        } catch (e) {
            cardNumbers = [];
        }
    } else if (Array.isArray(raw)) {
        cardNumbers = raw;
    } else {
        // Tipo inesperado, tentar converter
        try {
            cardNumbers = JSON.parse(JSON.stringify(raw));
        } catch (e) {
            cardNumbers = [];
        }
    }

    // Filtra por cardId
    const list = cardNumbers.filter(c => String(c.card_id) === String(cardId));

    // Limpa opções existentes e adiciona placeholder
    select.innerHTML = '';
    const emptyOpt = document.createElement('option');
    emptyOpt.value = '';
    emptyOpt.text = '---';
    select.appendChild(emptyOpt);

    if (list.length === 0) {
        wrapper.style.display = 'none';
        wrapper.classList.remove('active');
        // Atualizar home_screen quando card_number é ocultado
        updateHomeScreenCheckbox();
        return;
    }

    list.forEach(n => {
        const opt = document.createElement('option');
        opt.value = n.id;
        opt.text = n.name ? `${n.name} (${n.number})` : n.number;
        select.appendChild(opt);
    });

    // Se houver um valor pré-selecionado no formulário, mantê-lo
    const pre = select.getAttribute('data-initial');
    if (pre) select.value = pre;

    wrapper.style.display = 'block';
    wrapper.classList.add('active');
    
    // Atualizar home_screen quando card_number aparece
    updateHomeScreenCheckbox();
}

// Quando um cartão é selecionado, popula o select de números de cartão relacionados a ele usando os dados injetados no template. Se nenhum cartão for selecionado, esconde o campo de número do cartão.
function cardChangeHandler(e) {
    const val = e && e.target ? e.target.value : e;
    populateCardNumbersForCard(val);
    // Atualizar home_screen quando muda de card
    updateHomeScreenCheckbox();
}

const attachCardChangeListener = () => {
    const el = document.getElementById('id_card');
    const selFromSelects = selects.card;
    let attached = false;

    if (el) {
        el.addEventListener('change', cardChangeHandler);
        attached = true;
    }

    if (selFromSelects && selFromSelects !== el) {
        selFromSelects.addEventListener('change', cardChangeHandler);
        attached = true;
    }

    return attached;
};

if (!attachCardChangeListener()) {
    document.addEventListener('DOMContentLoaded', () => {
        const attached = attachCardChangeListener();
            // Também executa a população inicial após DOMContentLoaded
        const el = document.getElementById('id_card') || selects.card;
        if (el) {
            populateCardNumbersForCard(el.value);
        }
    });
} else {
    // Se o elemento já existir agora, também executar a população inicial imediatamente
    const el = document.getElementById('id_card') || selects.card;
    if (el) {
        populateCardNumbersForCard(el.value);
    }
}

/**
 * Inicializar listeners para account e card_number mudar home_screen
 */
function initializeHomeScreenListeners() {
    const accountSelect = document.getElementById('id_account');
    const cardNumberSelect = document.getElementById('id_card_number');
    
    if (accountSelect) {
        accountSelect.addEventListener('change', updateHomeScreenCheckbox);
    }
    
    if (cardNumberSelect) {
        cardNumberSelect.addEventListener('change', updateHomeScreenCheckbox);
    }
}

/**
 * Settar data-initial no card_number para preservar valor pré-selecionado
 */
function setCardNumberInitial() {
    const sel = document.getElementById('id_card_number');
    // Tentar pegar do template renderizado
    const initialValue = sel && sel.value ? sel.value : '';
    if (sel && initialValue) {
        sel.setAttribute('data-initial', initialValue);
    }
}

// Executar ao carregar o documento
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        setCardNumberInitial();
        initializeHomeScreenListeners();
        updateHomeScreenCheckbox();
    });
} else {
    setCardNumberInitial();
    initializeHomeScreenListeners();
    updateHomeScreenCheckbox();
}
