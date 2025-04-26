import { divs, selects } from '../layout/elements/transaction-form-elements.js';
import * as services from '../data/services.js';
// import * as tables from '../layout/elements/tables.js';

const fileInput = document.querySelector('#id_file');
const importBtn = document.querySelector('#import-btn');
const boxTransactions = document.querySelector('#box-transactions');
const transactionRows = document.querySelector('#transaction-rows');
const checkboxCheckAll = document.querySelector('#checkall');
const sendTransactionsBtn = document.querySelector('#send-transactions-btn');

selects.paymentMethod.value = 2;
divs.card.classList.add('toggled');

/**
 * Configura os selects relacionados ao meio de pagamento.
 */
export function selectPaymentMethod() {
    const paymentMethod = selects.paymentMethod.value;
    if (paymentMethod == 1) {
        divs.account.classList.add('toggled');
        divs.card.classList.remove('toggled');
        selects.card.required = true;
        selects.account.required = false;
        selects.account.selectedIndex = 0;
    } else {
        divs.card.classList.add('toggled');
        divs.account.classList.remove('toggled');
        selects.account.required = true;
        selects.card.required = false;
        selects.card.selectedIndex = 0;
    }
}

/**
 * Verifica se o arquivo foi enviado e se o meio de pagamento foi selecionado.
 * Se tudo estiver correto, envia o arquivo para o backend.
 */
async function sendFile() {
    const formData = new FormData();

    formData.append('file', fileInput.files[0]);
    formData.append('account', isNaN(parseInt(selects.account.value)) ? '' : parseInt(selects.account.value));
    formData.append('card', isNaN(parseInt(selects.card.value)) ? '' : parseInt(selects.card.value));

    if (!fileInput.files[0]) {
        alert('Selecione um arquivo para continuar.');
        return;
    }
    if (selects.paymentMethod.value == 1 && !selects.card.value) {
        alert('Selecione um cartão para continuar.');
    } else if (selects.paymentMethod.value == 2 && !selects.account.value) {
        alert('Selecione uma conta para continuar.');
    } else {
        const transactions = await services.importTransactions(formData);
        window.myFinance = window.myFinance || {};
        window.myFinance.importedTransactions = transactions;
        const importError = document.querySelector('#import-error');
        if (transactions.errors) {
            importError.classList.remove('toggled');
            importError.textContent = transactions.errors;
        } else {
            importError.classList.add('toggled');
            renderBox(transactions);
        }
    }
}

/**
 * Método principal que renderiza a tabela de transações importadas.
 *
 * As colunas da tabela são: data, descrição, valor, categoria, subcategoria e conta/cartão.
 *
 * @param {array} transactions - Um array de transações importadas do arquivo da instituição financeira.
 */
async function renderBox(transactions) {
    const categories = await services.getResource('categories');

    boxTransactions.classList.remove('toggled');
    transactionRows.innerHTML = '';

    for (const transaction of transactions) {
        const row = document.createElement('tr');
        const subcategories = await services.getChildrenResource('categories', 'subcategories', transaction.category);
        const fields = getTransactionFields(transaction, categories, subcategories);
        renderFields(row, fields);
        transactionRows.appendChild(row);
    }
}

/**
 * Método acessório de renderBox que cria a lista das colunas com as configurações dos campos a serem renderizados.
 *
 * @param {Object} transaction - Os lançamentos provenientes do arquivo de importação
 * @param {Object} categories - As categorias cadastradas no banco.
 * @param {Object} subcategories - As subcategorias cadastradas no banco.
 * @returns Uma lista de objetos literais com os campos a serem renderizados.
 */
function getTransactionFields(transaction, categories, subcategories) {
    return [
        {
            type: 'checkbox',
            id: transaction.id,
            render: (cell, row) => {
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.id = transaction.id;

                checkbox.addEventListener('change', () => {
                    row.classList.toggle('row-disabled', !checkbox.checked);
                });

                if (!checkbox.checked) {
                    row.classList.add('row-disabled');
                }

                cell.appendChild(checkbox);
            },
        },
        {
            id: `id_date_${transaction.id}`,
            type: 'date',
            value: transaction.date,
        },
        {
            id: `id_category_${transaction.id}`,
            type: 'select',
            options: categories,
            selected: transaction.category,
            onChange: async (select, cell) => {
                const subcategorySelect = cell.nextSibling.querySelector('select');
                const subcategories = await services.getChildrenResource('categories', 'subcategories', select.value);
                updateSelectOptions(subcategorySelect, subcategories);
            },
        },
        {
            id: `id_subcategory_${transaction.id}`,
            type: 'select',
            options: subcategories,
            selected: transaction.subcategory,
        },
        {
            id: `id_description_${transaction.id}`,
            type: 'text',
            value: transaction.description,
        },
        {
            id: `id_value_${transaction.id}`,
            type: 'text',
            value: transaction.value,
            disabled: true,
        },
    ];
}

/**
 * Método acessório de renderBox que renderiza o array dos campos configurados transformando-os em
 * campos com valores editáveis.
 *
 * @param {Object} row Elemento TR
 * @param {Array} fields Os campos a serem renderizados na linha.
 */
function renderFields(row, fields) {
    fields.forEach((field) => {
        const cell = row.insertCell();

        if (field.render) {
            field.render(cell, row);
            return;
        }

        let element;

        if (field.type === 'select') {
            element = createSelect(field);
        } else {
            element = createInput(field);
        }

        cell.appendChild(element);

        if (field.onChange && field.type === 'select') {
            element.addEventListener('change', () => field.onChange(element, cell));
        }
    });
}

/**
 * Método acessório de renderFields que cria inputs.
 *
 * @param {Object} field - O campo a ser renderizado na coluna.
 * @returns Um elemento HTML de input.
 */
function createInput(field) {
    const input = document.createElement('input');
    input.type = field.type || 'text';
    input.id = field.id;
    input.value = field.value || '';
    input.classList.add('form-control');
    if (field.disabled) input.disabled = true;
    return input;
}

/**
 * Método acessório de renderFields que cria selects.
 *
 * @param {Object} field - O campo a ser renderizado na coluna.
 * @returns Um elemento HTML de select.
 */
function createSelect(field) {
    const select = document.createElement('select');
    select.id = field.id;
    select.classList.add('form-control');

    field.options.forEach((opt) => {
        const option = document.createElement('option');
        option.value = opt.id;
        option.textContent = opt.description;
        if (opt.id === field.selected) option.selected = true;
        select.appendChild(option);
    });

    return select;
}

/**
 * Método acessório de getTransactionFields que cria as options para um select.
 *
 * @param {Object} select - Um Objeto HTML do tipo select.
 * @param {Array} options - Uma lista de options para o select.
 */
function updateSelectOptions(select, options) {
    select.innerHTML = '';
    options.forEach((opt) => {
        const option = document.createElement('option');
        option.value = opt.id;
        option.textContent = opt.description;
        select.appendChild(option);
    });
}

/**
 * Envia as transações selecionadas para o backend.
 * Faz a validação dos dados e cadastra as transações no banco de dados.
 *
 * @param {array} transactions - Um array de transações importadas do arquivo da instituição financeira.
 *
 * @returns - Redireciona para a tela de relatório financeiro.
 */
async function importTransactions(transactions) {
    const selectedIds = getSelectedTransactionIds();

    for (let transaction of transactions) {
        if (!selectedIds.includes(transaction.id)) continue;

        const newTransaction = getFormData(transaction.id);
        const feedback = buildFeedback(transaction, newTransaction);

        const created = await createNewResource('transactions', newTransaction, true);
        if (!created) return;

        if (feedback) {
            await services.createResource('categorization-feedback', JSON.stringify(feedback));
        }
    }

    // Envia para o backend uma requisição para treinar o Transaction Classifier a partir dos feedbacks
    services.retrainFromFeedback();

    // Redireciona para o mês atual
    window.location.href = '/relatorio_financeiro/mes_atual/';
}

/**
 * Método acessório de importTransactions que retorna os IDs das transações selecionadas pelo usuário.
 */
function getSelectedTransactionIds() {
    const ids = [];
    for (let row of transactionRows.children) {
        const checkbox = row.firstChild.firstChild;
        if (checkbox.checked) {
            ids.push(parseInt(checkbox.id));
        }
    }
    return ids;
}

/**
 * Método acessório de importTransactions que coleta os dados do formulário da transação com base no ID.
 */
function getFormData(transactionId) {
    return {
        release_date: document.getElementById(`id_date_${transactionId}`).value,
        account: document.getElementById('id_account').value,
        card: document.getElementById('id_card').value,
        category: document.getElementById(`id_category_${transactionId}`).value,
        subcategory: document.getElementById(`id_subcategory_${transactionId}`).value,
        description: document.getElementById(`id_description_${transactionId}`).value,
        value: document.getElementById(`id_value_${transactionId}`).value,
    };
}

/**
 * Método acessório de importTransactions que compara os dados da predição com os dados corrigidos pelo usuário.
 *
 * @param {Object} original - Um objeto de transaction oriundo da importação do arquivo.
 * @param {Object} updated - Um objeto de transaction oriundo do formulário.
 * @returns O feedback de categorização, se houver alteração.
 */
function buildFeedback(original, updated) {
    const categoryChanged = original.category !== updated.category;
    const subcategoryChanged = original.subcategory !== updated.subcategory;
    const descriptionChanged = original.description !== updated.description;

    if (!(categoryChanged || subcategoryChanged || descriptionChanged)) return null;

    return {
        description: original.description,
        predicted_category_id: original.category,
        predicted_subcategory_id: original.subcategory,
        corrected_description: updated.description,
        corrected_category_id: updated.category,
        corrected_subcategory_id: updated.subcategory,
    };
}

/**
 * Método acessório de importTransactions que cria um novo recurso no backend via requisição POST.
 *
 * @param {string} endpoint - Nome do endpoint da API (ex: 'transactions', 'categorization-feedback').
 * @param {object|string} data - Dados a serem enviados. Se for objeto, será convertido para JSON.
 * @param {boolean} [useAwait=false] - Se verdadeiro, aguarda a resposta antes de continuar.
 * @returns {Promise<object|null>} - Retorna a resposta em JSON, ou false em caso de erro.
 */
async function createNewResource(model, instance) {
    const importError = document.querySelector('#import-error');

    const response = await services.createResource(model, JSON.stringify(instance));
    try {
        importError.classList.add('toggled');

        if (response instanceof Error) {
            throw new Error(response.message);
        }
        return response;
    } catch (error) {
        importError.classList.remove('toggled');
        importError.textContent = `${error.message}: ${JSON.stringify(instance)}`;
        return false;
    }
}

importBtn.addEventListener('click', () => sendFile());

selects.paymentMethod.addEventListener('change', () => selectPaymentMethod());

checkboxCheckAll.addEventListener('change', function () {
    for (const row of transactionRows.children) {
        const checkbox = row.children[0].children[0];
        checkbox.checked = this.checked;

        // Adiciona ou remove a classe 'row-disabled' com base no estado do checkbox
        if (checkbox.checked) {
            row.classList.remove('row-disabled');
        } else {
            row.classList.add('row-disabled');
        }
    }
});

sendTransactionsBtn.addEventListener('click', () => {
    const transactions = window.myFinance.importedTransactions;
    importTransactions(transactions);
});
