import { divs, selects } from '../layout/elements/transaction-form-elements.js';
import * as services from '../data/services.js';

const fileInput = document.querySelector('#id_file');
const importBtn = document.querySelector('#import-btn');
const boxTransactions = document.querySelector('#box-transactions');
const transactionRows = document.querySelector('#transaction-rows');
const checkboxCheckAll = document.querySelector('#checkall');
const sendTransactionsBtn = document.querySelector('#send-transactions-btn');
const fileTypeConfigurableCSV = document.querySelector('#file-type-configurable-csv');
const fileTypeTasker = document.querySelector('#file-type-tasker');
const targetModelSelect = document.querySelector('#id_target_model');
const csvImportConfigSelect = document.querySelector('#id_csv_import_config');
const investmentImportTypeGroup = document.querySelector('#investment-import-type-group');
const investmentImportTypeSelect = document.querySelector('#id_investment_import_type');
const dateColumnInput = document.querySelector('#id_date_column');
const descriptionColumnInput = document.querySelector('#id_description_column');
const valueColumnInput = document.querySelector('#id_value_column');
const installmentColumnInput = document.querySelector('#id_installment_column');
const installmentFormatInput = document.querySelector('#id_installment_format');
const configurableCSVFields = document.querySelector('#configurable-csv-fields');
const csvConfigManagedFields = document.querySelectorAll('.csv-config-managed');
const csvFileLabel = document.querySelector('#csv-file-label');
const importHeadings = document.querySelectorAll('.import-heading');
const importCardNumberHeading = document.querySelector('.import-card-number-heading');
const importInstallmentHeading = document.querySelector('.import-installment-heading');
const paymentMethodGroup = document.querySelector('#payment-method-group');
const paymentTargetFields = document.querySelector('#payment-target-fields');

const targetModels = {
    statement: 'statement_transaction',
    investment: 'investments_investmenttransaction',
};

const investmentTransactionTypes = [
    { id: 'aporte', description: 'Depósito' },
    { id: 'rendimento', description: 'Provento (dividendo/JCP)' },
];

selects.paymentMethod.value = 2;
divs.card.classList.add('toggled');

/**
 * Configura os selects relacionados ao meio de pagamento.
 */
export function selectPaymentMethod() {
    if (isConfigurableCSV() && getTargetModel() === targetModels.investment) {
        divs.account.classList.add('toggled');
        divs.card.classList.add('toggled');
        selects.account.required = false;
        selects.card.required = false;
        return;
    }

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
    const csvImportConfig = getSelectedCSVImportConfig();

    formData.append('file', fileInput.files[0]);
    formData.append('account', isNaN(parseInt(selects.account.value)) ? '' : parseInt(selects.account.value));
    formData.append('card', isNaN(parseInt(selects.card.value)) ? '' : parseInt(selects.card.value));
    formData.append('csv_import_config', csvImportConfig ? csvImportConfig.id : '');
    formData.append('csv_mode', 'configurable');
    formData.append('target_model', getTargetModel());
    formData.append('date_column', dateColumnInput.value.trim());
    formData.append('description_column', descriptionColumnInput.value.trim());
    formData.append('value_column', valueColumnInput.value.trim());
    formData.append('installment_column', installmentColumnInput ? installmentColumnInput.value.trim() : '');
    formData.append('installment_format', installmentFormatInput ? installmentFormatInput.value : 'auto');
    formData.append('matching_fields', csvImportConfig ? csvImportConfig.matching_fields.join(',') : '');

    if (!fileInput.files[0]) {
        alert('Selecione um arquivo para continuar.');
        return;
    }
    if (!csvImportConfig || !dateColumnInput.value.trim() || !descriptionColumnInput.value.trim() || !valueColumnInput.value.trim()) {
        alert('Selecione uma configuração de CSV com as colunas de data, descrição e valor.');
        return;
    }
    if (getTargetModel() === targetModels.statement && selects.paymentMethod.value == 1 && !selects.card.value) {
        alert('Selecione um cartão para continuar.');
    } else if (getTargetModel() === targetModels.statement && selects.paymentMethod.value == 2 && !selects.account.value) {
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
    const isInvestmentImport = isConfigurableCSV() && getTargetModel() === targetModels.investment;
    const categories = isInvestmentImport ? [] : await services.getCategoriesByType('saida');
    const investments = isInvestmentImport ? await services.getResource('investments') : [];

    boxTransactions.classList.remove('toggled');
    transactionRows.innerHTML = '';
    window.myFinance.hasCSVInstallments = transactions.some((transaction) => transaction.installment_text);
    renderHeadings(isInvestmentImport);

    for (const transaction of transactions) {
        const row = document.createElement('tr');
        if (transaction.is_duplicate) {
            row.classList.add('row-duplicate');
            row.title = `Duplicado do lançamento #${transaction.duplicate_id}`;
        }
        const subcategories = isInvestmentImport
            ? []
            : await services.getChildrenResource('categories', 'subcategories', transaction.category);
        const fields = isInvestmentImport
            ? getInvestmentTransactionFields(transaction, investments)
            : getTransactionFields(transaction, categories, subcategories);
        renderFields(row, fields);
        transactionRows.appendChild(row);
    }
}

function renderHeadings(isInvestmentImport) {
    const headings = isInvestmentImport
        ? ['Data', 'Investimento', 'Tipo', 'Descrição', 'Valor']
        : ['Data', 'Categoria', 'Subcategoria', 'Descrição', 'Valor'];
    const shouldShowCardNumber = !isInvestmentImport && getCardNumbersByCard(selects.card.value).length > 0;

    if (importCardNumberHeading) {
        importCardNumberHeading.classList.toggle('hide', !shouldShowCardNumber);
    }

    if (importInstallmentHeading) {
        importInstallmentHeading.classList.toggle(
            'hide',
            isInvestmentImport || !(window.myFinance && window.myFinance.hasCSVInstallments)
        );
    }

    importHeadings.forEach((heading, index) => {
        heading.textContent = headings[index];
    });
}

/**
 * Método acessório de renderBox que cria a lista das colunas com as configurações dos campos a serem renderizados.
 *
 * @param {Object} transaction - Os lançamentos provenientes do arquivo de importação
 * @param {Object} categories - As categorias cadastradas no banco.
 * @param {Object} subcategories - As subcategorias cadastradas no banco.
 * @param {Boolean} isNotification - Se é notificação ou transação de arquivo.
 * @returns Uma lista de objetos literais com os campos a serem renderizados.
 */
function getTransactionFields(transaction, categories, subcategories) {
    const fields = [
        getCheckboxField(transaction),
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
            title: `Original: ${transaction.original_description}`,
        },
        {
            id: `id_value_${transaction.id}`,
            type: 'text',
            value: transaction.value,
            disabled: true,
        },
    ];

    const cardNumbers = getCardNumbersByCard(transaction.card || selects.card.value);
    if (cardNumbers.length > 0) {
        fields.splice(2, 0, {
            id: `id_card_number_${transaction.id}`,
            type: 'select',
            options: cardNumbers.map((cardNumber) => ({
                id: cardNumber.id,
                description: cardNumber.name || cardNumber.number,
            })),
            selected: transaction.card_number || cardNumbers[0].id,
        });
    }

    if (window.myFinance && window.myFinance.hasCSVInstallments) {
        fields.splice(2 + (cardNumbers.length > 0 ? 1 : 0), 0, {
            id: `id_installment_text_${transaction.id}`,
            type: 'text',
            value: transaction.installment_text || '',
        });
    }

    return fields;
}

function getInvestmentTransactionFields(transaction, investments) {
    return [
        getCheckboxField(transaction),
        {
            id: `id_date_${transaction.id}`,
            type: 'date',
            value: transaction.date,
        },
        {
            id: `id_investment_${transaction.id}`,
            type: 'select',
            options: investments,
        },
        {
            id: `id_investment_type_${transaction.id}`,
            type: 'select',
            options: investmentTransactionTypes,
            selected: getInvestmentImportType(),
        },
        {
            id: `id_description_${transaction.id}`,
            type: 'text',
            value: transaction.description,
            title: `Original: ${transaction.original_description}`,
        },
        {
            id: `id_value_${transaction.id}`,
            type: 'text',
            value: transaction.value,
        },
    ];
}

function getCheckboxField(transaction) {
    return {
        type: 'checkbox',
        id: transaction.id,
        render: (cell, row) => {
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.id = transaction.id;
            checkbox.checked = !transaction.is_duplicate;
            checkbox.disabled = Boolean(transaction.is_duplicate);

            checkbox.addEventListener('change', () => {
                row.classList.toggle('row-disabled', !checkbox.checked);
            });

            if (!checkbox.checked) {
                row.classList.add('row-disabled');
            }

            cell.appendChild(checkbox);
        },
    };
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
        applyImportCellClass(cell, field);

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

function applyImportCellClass(cell, field) {
    const fieldId = String(field.id || '');
    if (field.type === 'checkbox') {
        cell.classList.add('import-col-check');
    } else if (fieldId.startsWith('id_date_')) {
        cell.classList.add('import-col-date');
    } else if (fieldId.startsWith('id_card_number_')) {
        cell.classList.add('import-col-card-number');
    } else if (fieldId.startsWith('id_installment_text_')) {
        cell.classList.add('import-col-installment');
    } else if (fieldId.startsWith('id_category_')) {
        cell.classList.add('import-col-category');
    } else if (fieldId.startsWith('id_subcategory_')) {
        cell.classList.add('import-col-subcategory');
    } else if (fieldId.startsWith('id_description_')) {
        cell.classList.add('import-col-description');
    } else if (fieldId.startsWith('id_value_')) {
        cell.classList.add('import-col-value');
    }
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
    if (field.title) {
        input.title = field.title;
    }
    if (input.type === 'date') {
        input.value = formatDateForInput(field.value || '');
    } else {
        input.value = field.value || '';
    }
    input.classList.add('form-control');
    if (input.id && input.id.startsWith('id_value_')) {
        input.maxLength = 9;
        input.pattern = '^[0-9]{1,6}(\\.[0-9]{2})?$';
        input.style.textAlign = 'right';
    }
    if (input.id && input.id.startsWith('id_description_')) {
        input.maxLength = 255;
    }
    if (field.disabled) input.disabled = true;
    return input;
}

function formatDateForInput(value) {
    if (!value) return '';
    if (typeof value === 'number') {
        const d = new Date(value);
        if (isNaN(d)) return '';
        return d.toISOString().slice(0, 10);
    }
    if (typeof value === 'string') {
        const isoMatch = value.match(/^(\d{4}-\d{2}-\d{2})/);
        if (isoMatch) return isoMatch[1];
        const brMatch = value.match(/^(\d{2})\/(\d{2})\/(\d{4})/);
        if (brMatch) return `${brMatch[3]}-${brMatch[2]}-${brMatch[1]}`;
        const parsed = new Date(value);
        if (!isNaN(parsed)) {
            const y = parsed.getFullYear();
            const m = String(parsed.getMonth() + 1).padStart(2, '0');
            const d = String(parsed.getDate()).padStart(2, '0');
            return `${y}-${m}-${d}`;
        }
    }
    return '';
}

/**
 * Método acessório de renderFields que cria selects.
 *
 * @param {Object} field - O campo a ser renderizado na coluna.
 * @returns Um elemento HTML de select.
 */
function createSelect(field) {
    const select = document.createElement('select');
    if (field.id) select.id = field.id;
    select.classList.add('form-control');

    if (!field.options || !Array.isArray(field.options) || field.options.length === 0) {
        const option = document.createElement('option');
        option.value = '';
        option.textContent = 'Nenhuma opção disponível';
        select.appendChild(option);
        return select;
    }

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
    const selectedIds = getSelectedTransactionIds(transactionRows);
    const isInvestmentImport = isConfigurableCSV() && getTargetModel() === targetModels.investment;

    for (let transaction of transactions) {
        if (!selectedIds.includes(transaction.id)) continue;

        const newTransaction = isInvestmentImport
            ? getInvestmentTransactionFormData(transaction.id)
            : getFormData(transaction.id, transaction);

        const created = await createNewResource(isInvestmentImport ? 'investment-transactions' : 'transactions', newTransaction);
        if (!created) return;

        const feedback = isInvestmentImport ? null : buildFeedback(transaction, newTransaction);
        if (feedback) {
            await services.createResource('categorization-feedback', JSON.stringify(feedback));
        }
    }

    if (!isInvestmentImport) {
        // Envia para o backend uma requisição para treinar o Transaction Classifier a partir dos feedbacks
        await services.sendRequisition('transaction-classifier/train', 'POST');
    }

    window.location.href = isInvestmentImport ? '/investimentos/' : '/relatorio_financeiro/mes_atual/';
}

/**
 * Método acessório de importTransactions que retorna os IDs das transações selecionadas pelo usuário.
 */
function getSelectedTransactionIds(rows = transactionRows) {
    const ids = [];
    for (let row of rows.children) {
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
function getFormData(transactionId, transactionObj = null) {
    return {
        posted_date: document.getElementById(`id_date_${transactionId}`).value,
        account: document.getElementById('id_account').value,
        card: document.getElementById('id_card').value,
        card_number: getCardNumberValue(transactionId),
        category: document.getElementById(`id_category_${transactionId}`).value,
        subcategory: document.getElementById(`id_subcategory_${transactionId}`).value,
        description: document.getElementById(`id_description_${transactionId}`).value,
        original_description: transactionObj ? transactionObj.original_description : '',
        value: document.getElementById(`id_value_${transactionId}`).value,
        installment_text: getInstallmentTextValue(transactionId, transactionObj),
        installment_value_mode: 'installment',
        matching_fields: transactionObj ? transactionObj.matching_fields || [] : [],
    };
}

function getCardNumberValue(transactionId) {
    const cardNumberSelect = document.getElementById(`id_card_number_${transactionId}`);
    return cardNumberSelect ? cardNumberSelect.value : '';
}

function getInstallmentTextValue(transactionId, transactionObj = null) {
    const installmentInput = document.getElementById(`id_installment_text_${transactionId}`);
    if (installmentInput) return installmentInput.value;
    return transactionObj ? transactionObj.installment_text || '' : '';
}

function getInvestmentTransactionFormData(transactionId) {
    return {
        date: document.getElementById(`id_date_${transactionId}`).value,
        investment: document.getElementById(`id_investment_${transactionId}`).value,
        type: document.getElementById(`id_investment_type_${transactionId}`).value,
        amount: document.getElementById(`id_value_${transactionId}`).value,
        notes: document.getElementById(`id_description_${transactionId}`).value,
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

// Event listeners - apenas adiciona se os elementos existem
if (importBtn) {
    importBtn.addEventListener('click', () => sendFile());
}

if (selects && selects.paymentMethod) {
    selects.paymentMethod.addEventListener('change', () => selectPaymentMethod());
}

if (targetModelSelect) {
    targetModelSelect.addEventListener('change', () => selectTargetModel());
}

if (csvImportConfigSelect) {
    csvImportConfigSelect.addEventListener('change', () => applySelectedCSVImportConfig());
}

if (fileTypeConfigurableCSV) {
    fileTypeConfigurableCSV.addEventListener('change', () => selectCSVMode());
}

if (fileTypeTasker) {
    fileTypeTasker.addEventListener('change', () => selectCSVMode());
}

if (checkboxCheckAll && transactionRows) {
    checkboxCheckAll.addEventListener('change', function () {
        for (const row of transactionRows.children) {
            const checkbox = row.children[0].children[0];
            if (checkbox.disabled) continue;
            checkbox.checked = this.checked;

            // Adiciona ou remove a classe 'row-disabled' com base no estado do checkbox
            if (checkbox.checked) {
                row.classList.remove('row-disabled');
            } else {
                row.classList.add('row-disabled');
            }
        }
    });
}

if (sendTransactionsBtn) {
    sendTransactionsBtn.addEventListener('click', () => {
        const transactions = window.myFinance.importedTransactions;
        importTransactions(transactions);
    });
}

function getTargetModel() {
    return targetModelSelect ? targetModelSelect.value : targetModels.statement;
}

function isConfigurableCSV() {
    return Boolean(fileTypeConfigurableCSV && fileTypeConfigurableCSV.checked);
}

function getInvestmentImportType() {
    return investmentImportTypeSelect ? investmentImportTypeSelect.value : 'aporte';
}

function getSelectedCSVImportConfig() {
    if (!csvImportConfigSelect || !csvImportConfigSelect.value) return null;
    const configs = (window.myFinance && window.myFinance.csvImportConfigs) || [];
    return configs.find((config) => String(config.id) === String(csvImportConfigSelect.value)) || null;
}

function getCardNumbersByCard(cardId) {
    if (!cardId) return [];
    const cardNumbers = (window.myFinance && window.myFinance.cardNumbers) || window.card_numbers_json || [];
    return cardNumbers.filter((cardNumber) => String(cardNumber.card_id) === String(cardId));
}

function applySelectedCSVImportConfig() {
    const config = getSelectedCSVImportConfig();
    if (!config) return;

    if (targetModelSelect) targetModelSelect.value = config.target_model;
    if (dateColumnInput) dateColumnInput.value = config.date_column;
    if (descriptionColumnInput) descriptionColumnInput.value = config.description_column;
    if (valueColumnInput) valueColumnInput.value = config.value_column;
    if (installmentColumnInput) installmentColumnInput.value = config.installment_column || '';
    if (installmentFormatInput) installmentFormatInput.value = config.installment_format || 'auto';
    if (selects.paymentMethod) selects.paymentMethod.value = config.payment_method;
    if (selects.account) selects.account.value = config.account || '';
    if (selects.card) selects.card.value = config.card || '';

    selectTargetModel();
}

function selectTargetModel() {
    const isInvestmentImport = isConfigurableCSV() && getTargetModel() === targetModels.investment;

    if (paymentMethodGroup && !isConfigurableCSV()) {
        paymentMethodGroup.classList.toggle('toggled', isInvestmentImport);
    }

    if (investmentImportTypeGroup) {
        investmentImportTypeGroup.classList.toggle('hide', !isInvestmentImport);
    }

    selectPaymentMethod();
}

function selectCSVMode() {
    const configurable = isConfigurableCSV();

    if (configurableCSVFields) {
        configurableCSVFields.classList.toggle('hide', !configurable);
    }

    csvConfigManagedFields.forEach((fieldGroup) => {
        fieldGroup.classList.add('hide');
    });

    if (paymentMethodGroup) {
        paymentMethodGroup.classList.toggle('hide', configurable);
    }

    if (paymentTargetFields) {
        paymentTargetFields.classList.toggle('hide', configurable);
    }

    if (csvFileLabel) {
        csvFileLabel.textContent = 'Arquivo CSV configurável: ';
    }

    if (importBtn) {
        importBtn.value = 'Importar CSV configurável';
    }

    selectTargetModel();
}

selectCSVMode();
