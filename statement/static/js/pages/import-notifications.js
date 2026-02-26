import * as services from '../data/services.js';

const notificationRows = document.querySelector('#section-notifications-import #notification-rows-section');
const checkboxCheckAllNotifications = document.querySelector('#checkall-notifications');
const sendNotificationsBtn = document.querySelector('#send-notifications-btn');
const radioImportNotifications = document.querySelector('#import-type-notifications');

/**
 * Renderiza a tabela de notificações para importação.
 *
 * @param {array} notifications - Um array de notificações convertidas em transações.
 */
async function renderNotificationsBox(notifications) {
    const categories = await services.getCategoriesByType('saida');
    try {
        const simpleList = Array.isArray(notifications) ? notifications.map(n => ({id: n.id, card_id: n.card_id, card_number_id: n.card_number_id})) : [];
        const _groups = {};
        if (Array.isArray(notifications)) {
            for (const n of notifications) {
                const key = `${n.card_id || 'none'}:${n.card_number_id || 'none'}`;
                _groups[key] = _groups[key] || [];
                _groups[key].push(n.id);
            }
        }
    } catch (e) {
        console.warn('Erro ao agrupar notificações', e);
    }

    const notificationRows = document.querySelector('#section-notifications-import #notification-rows-section');
    notificationRows.innerHTML = '';
    notificationRows.style.display = 'table-row-group';
    const section = document.getElementById('section-notifications-import');
    if (section) section.style.display = 'block';
    const table = notificationRows ? notificationRows.closest('table') : null;
    // remove previously generated group tbodies
    if (table) {
        table.querySelectorAll('tbody.generated-group').forEach(t => t.remove());
    }


    // build group map so we can render a tbody per group (card_id:card_number_id)
    const groups = new Map();
    const COLSPAN = 6;
    for (const notification of notifications) {
        try {
            const row = document.createElement('tr');
            const subcategories = notification.category ? await services.getChildrenResource('categories', 'subcategories', notification.category) : [];
            const fields = getTransactionFields(notification, categories, subcategories);
            renderFields(row, fields);
            // determine group key
            const gkey = `${notification.card_id || 'none'}:${notification.card_number_id || 'none'}`;
            let tbody = groups.get(gkey);
            if (!tbody) {
                tbody = document.createElement('tbody');
                tbody.classList.add('generated-group');
                tbody.dataset.groupKey = gkey;
                // create header row for the group
                const header = document.createElement('tr');
                header.classList.add('group-header');
                const headerCell = document.createElement('td');
                headerCell.colSpan = COLSPAN;
                const cardLabel = notification.card_description || `Cartão ${notification.card_id || ''}`;
                const numberLabel = notification.card_number_display ? ` - ${notification.card_number_display}` : '';
                headerCell.textContent = `${cardLabel}${numberLabel}`;
                header.appendChild(headerCell);
                tbody.appendChild(header);
                groups.set(gkey, tbody);
            }
            tbody.appendChild(row);
            // Popula o select de subcategorias com base no valor atualmente selecionado
            // no select de categoria (padrão: primeira categoria). Isso garante que
            // mesmo quando a notificação não traz categoria prevista, o select de
            // subcategoria mostre as opções corretas.
            const categorySelect = document.getElementById(`id_category_${notification.id}`);
            const subcategorySelect = document.getElementById(`id_subcategory_${notification.id}`);
            if (categorySelect && subcategorySelect) {
                let selectedCategory = categorySelect.value;
                // If no category is explicitly selected, pick the first meaningful option
                if (!selectedCategory || parseInt(selectedCategory, 10) <= 0) {
                    const firstOpt = Array.from(categorySelect.options).find(o => {
                        const v = parseInt(o.value, 10);
                        return !isNaN(v) && v > 0;
                    });
                    if (firstOpt) selectedCategory = firstOpt.value;
                }

                if (selectedCategory && parseInt(selectedCategory, 10) > 0) {
                    const subcats = await services.getChildrenResource('categories', 'subcategories', selectedCategory);
                    updateSelectOptions(subcategorySelect, subcats);
                    if (notification.subcategory) subcategorySelect.value = notification.subcategory;
                }
            }
            notificationRows.style.display = 'table-row-group';
            row.style.display = 'table-row';
            row.style.visibility = 'visible';
            row.style.opacity = '1';
        } catch (error) {
            console.error('Erro ao renderizar notificação:', notification, error);
        }
    }

    // append all generated group tbodies to the table
    if (table) {
        for (const tbody of groups.values()) {
            table.appendChild(tbody);
        }
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
            render: (cell) => {
                const input = document.createElement('input');
                input.type = 'date';
                input.id = `id_date_${transaction.id}`;
                input.value = transaction.date;
                input.classList.add('form-control');
                cell.appendChild(input);
            },
        },
        {
            id: `id_category_${transaction.id}`,
            type: 'select',
            options: categories,
            selected: transaction.category,
            onChange: async (selectElem, cell) => {
                const subcategorySelect = document.getElementById(`id_subcategory_${transaction.id}`) || cell.nextSibling.querySelector('select');
                const subcategories = await services.getChildrenResource('categories', 'subcategories', selectElem.value);
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
            render: (cell) => {
                const input = document.createElement('input');
                input.type = 'text';
                input.id = `id_description_${transaction.id}`;
                input.value = transaction.description;
                input.title = `Original: ${transaction.original_description}`;
                input.classList.add('form-control');
                cell.appendChild(input);
            },
        },
        {
            id: `id_value_${transaction.id}`,
            type: 'number',
            value: transaction.value,
            disabled: false,
            render: (cell) => {
                const input = document.createElement('input');
                input.type = 'number';
                input.step = '0.01';
                input.min = '0';
                input.inputMode = 'decimal';
                input.id = `id_value_${transaction.id}`;
                input.value = transaction.value;
                input.classList.add('form-control');
                cell.appendChild(input);
            },
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
        try {
            const cell = row.insertCell();

                if (field.render) {
                    field.render(cell, row);
                } else {
                    let element;
                    if (field.type === 'select') {
                        element = createSelect(field);
                    } else {
                        element = createInput(field);
                    }
                    if (element) {
                        cell.appendChild(element);
                    }
                }

                // Ajusta largura da célula para valor/descrição garantindo layout
                const fid = String(field.id || '');
                if (fid.startsWith('id_value_')) {
                    cell.classList.add('value-cell');
                    cell.style.setProperty('max-width', '120px', 'important');
                    cell.style.setProperty('min-width', '0px', 'important');
                    cell.style.whiteSpace = 'nowrap';
                    cell.style.overflow = 'hidden';
                } else if (fid.startsWith('id_description_')) {
                    cell.classList.add('description-cell');
                    cell.style.setProperty('min-width', '360px', 'important');
                }

                // Adiciona listener de change para selects (se aplicável)
                if (field.onChange && field.type === 'select') {
                    const selectElem = cell.querySelector('select');
                    if (selectElem) selectElem.addEventListener('change', () => field.onChange(selectElem, cell));
                }
        } catch (error) {
            console.error('Erro ao renderizar field:', field, error);
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
    if (field.title) {
        input.title = field.title;
    }
    // format date values to yyyy-mm-dd for date inputs so browser doesn't default to today
    if (input.type === 'date') {
        input.value = formatDateForInput(field.value || '');
    } else {
        input.value = field.value || '';
    }
    input.classList.add('form-control');
    // Ajustes de tamanho e limites específicos para campos description/value
    if (input.id && input.id.startsWith('id_value_')) {
        // Numeric input: up to 6 digits + 2 decimals. Use number type attributes.
        input.type = 'number';
        input.step = '0.01';
        input.min = '0';
        input.inputMode = 'decimal';
        input.maxLength = 9; // visual limit (doesn't strictly limit number input in all browsers)
        input.pattern = '^[0-9]{1,6}(\\.[0-9]{2})?$';
        // input ocupa 100% da célula, mas também define max-width para proteção contra CSS global
        input.style.setProperty('width', '100%', 'important');
        input.style.setProperty('max-width', '120px', 'important');
        input.style.setProperty('box-sizing', 'border-box', 'important');
        input.style.textAlign = 'right';
        input.classList.add('value-input');
    }
    if (input.id && input.id.startsWith('id_description_')) {
        // garantir que a descrição tenha espaço suficiente
        input.maxLength = 255;
        input.style.setProperty('width', '100%', 'important');
        input.style.setProperty('min-width', '300px', 'important');
        input.classList.add('description-input');
    }
    if (field.disabled) input.disabled = true;
    return input;
}

/**
 * Formata diferentes formatos de data para o padrão aceito por input[type=date]: YYYY-MM-DD
 * Aceita: 'YYYY-MM-DD', 'YYYY-MM-DDTHH:MM:SS', 'DD/MM/YYYY', timestamps, e strings parseáveis pelo Date.
 */
function formatDateForInput(value) {
    if (!value) return '';
    if (typeof value === 'number') {
        const d = new Date(value);
        if (isNaN(d)) return '';
        return d.toISOString().slice(0, 10);
    }
    if (typeof value === 'string') {
        // Already ISO-like
        const isoMatch = value.match(/^(\d{4}-\d{2}-\d{2})/);
        if (isoMatch) return isoMatch[1];

        // DD/MM/YYYY
        const brMatch = value.match(/^(\d{2})\/(\d{2})\/(\d{4})/);
        if (brMatch) return `${brMatch[3]}-${brMatch[2]}-${brMatch[1]}`;

        // Try Date parsing
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

    if (!field.options) {
        console.warn('Opções vazias para select:', field.id);
        const option = document.createElement('option');
        option.value = '';
        option.textContent = 'Nenhuma opção disponível';
        select.appendChild(option);
        return select;
    }

    if (Array.isArray(field.options)) {
        field.options.forEach((opt) => {
            const option = document.createElement('option');
            option.value = opt.id;
            option.textContent = opt.description;
            if (opt.id === field.selected) option.selected = true;
            select.appendChild(option);
        });
    }

    return select;
}

/**
 * Método acessório de getTransactionFields que cria as options para um select.
 *
 * @param {Object} select - Um Objeto HTML do tipo select.
 * @param {Array} options - Uma lista de options para o select.
 */
function updateSelectOptions(select, options) {
    if (!select) return;
    select.innerHTML = '';
    const defaultOpt = document.createElement('option');
    select.appendChild(defaultOpt);
    options.forEach((opt) => {
        const option = document.createElement('option');
        option.value = opt.id;
        option.textContent = opt.description;
        select.appendChild(option);
    });
}

/**
 * Marca um array de notificações como usadas no backend.
 *
 * @param {array} notificationIds - Array com os IDs das notificações a marcar como usadas.
 */
async function markNotificationsAsUsed(notificationIds) {
    for (const notificationId of notificationIds) {
        try {
            await fetch(`/api/notifications/${notificationId}/`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                },
                body: JSON.stringify({ is_used: true }),
            });
        } catch (error) {
            console.error(`Erro ao marcar notificação ${notificationId} como usada:`, error);
        }
    }
}

/**
 * Obtém o valor de um cookie pelo nome.
 *
 * @param {string} name - Nome do cookie.
 * @returns {string} Valor do cookie ou string vazia se não encontrado.
 */
function getCookie(name) {
    let cookieValue = '';
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

/**
 * Envia as notificações selecionadas para o backend.
 * Faz a validação dos dados e cadastra as transações no banco de dados.
 *
 * @param {array} notifications - Um array de notificações convertidas em transações.
 */
async function importNotifications(notifications) {
    const selectedIds = getSelectedNotificationIds();
    const notificationsToMarkAsUsed = [];

    for (let notification of notifications) {
        if (!selectedIds.includes(notification.id)) continue;

        const newTransaction = getFormData(notification.id, notification);
        const feedback = buildFeedback(notification, newTransaction);

        const created = await createNewResource('transactions', newTransaction, true);
        if (!created) return;

        if (feedback) {
            await services.createResource('categorization-feedback', JSON.stringify(feedback));
        }

        // Coleta o ID para marcar como usada
        if (notification.notification_id) {
            notificationsToMarkAsUsed.push(notification.notification_id);
        }
    }

    // Marca as notificações como usadas
    if (notificationsToMarkAsUsed.length > 0) {
        await markNotificationsAsUsed(notificationsToMarkAsUsed);
    }

    // Envia para o backend uma requisição para treinar o Transaction Classifier a partir dos feedbacks
    await services.sendRequisition('transaction-classifier/train', 'POST');

    // Redireciona para o mês atual
    window.location.href = '/relatorio_financeiro/mes_atual/';
}

/**
 * Método acessório de importNotifications que retorna os IDs das notificações selecionadas pelo usuário.
 */
function getSelectedNotificationIds() {
    const ids = [];
    const rows = document.querySelectorAll('#section-notifications-import tbody.generated-group tr');
    rows.forEach((row) => {
        if (row.classList.contains('group-header')) return; // skip header rows
        const checkbox = row.querySelector('input[type="checkbox"]');
        if (checkbox && checkbox.checked) ids.push(parseInt(checkbox.id, 10));
    });
    return ids;
}

/**
 * Método acessório de importNotifications que coleta os dados do formulário da transação com base no ID.
 */
function getFormData(notificationId, notificationObj) {
    return {
        posted_date: document.getElementById(`id_date_${notificationId}`).value,
        card: notificationObj.card_id,
        card_number: notificationObj.card_number_id || null,
        category: document.getElementById(`id_category_${notificationId}`).value,
        subcategory: document.getElementById(`id_subcategory_${notificationId}`).value,
        description: document.getElementById(`id_description_${notificationId}`).value,
        value: document.getElementById(`id_value_${notificationId}`).value,
    };
}

/**
 * Método acessório de importNotifications que compara os dados da predição com os dados corrigidos pelo usuário.
 *
 * @param {Object} original - Um objeto de notificação oriundo da listagem.
 * @param {Object} updated - Um objeto de transação oriundo do formulário.
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
 * Método acessório de importNotifications que cria um novo recurso no backend via requisição POST.
 *
 * @param {string} endpoint - Nome do endpoint da API (ex: 'transactions', 'categorization-feedback').
 * @param {object|string} data - Dados a serem enviados. Se for objeto, será convertido para JSON.
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
if (checkboxCheckAllNotifications && notificationRows) {
    checkboxCheckAllNotifications.addEventListener('change', function () {
        for (const row of notificationRows.children) {
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
}

if (sendNotificationsBtn) {
    sendNotificationsBtn.addEventListener('click', () => {
        const notifications = window.myFinance.notifications;
        importNotifications(notifications);
    });
}

if (radioImportNotifications) {
    radioImportNotifications.addEventListener('change', async (e) => {
        if (e.target.checked) {
            // Exibe a seção de notificações
            const section = document.getElementById('section-notifications-import');
            section.classList.remove('toggled');
            // Oculta outras seções
            const fileSection = document.getElementById('section-file-import');
            fileSection.classList.add('toggled');
            // Renderiza as notificações
            const notifications = window.myFinance.notifications;
            await renderNotificationsBox(notifications);
        }
    });
}

// Inicializa a renderização das notificações assim que o módulo carrega
(async () => {
    const radioImportNotifications = document.querySelector('#import-type-notifications');
    const notifications = window.myFinance ? window.myFinance.notifications : [];

    // Se o radio de importação por notificações estiver selecionado,
    // sempre exibe a seção de notificações (mesmo que esteja vazia) e
    // oculta a seção de importação por arquivo. Só renderiza as linhas
    // quando houver notificações.
    if (radioImportNotifications && radioImportNotifications.checked) {
        const section = document.getElementById('section-notifications-import');
        const fileSection = document.getElementById('section-file-import');
        const notificationRows = document.getElementById('notification-rows-section');

        if (section) {
            section.classList.remove('toggled');
            section.style.display = 'block';
        }
        if (fileSection) fileSection.classList.add('toggled');

        if (notifications && notifications.length > 0) {
            if (notificationRows) notificationRows.style.display = 'table-row-group';
            await renderNotificationsBox(notifications);
        } else if (notificationRows) {
            // quando não há notificações, garante que a tabela esteja oculta
            // e a mensagem "Nenhuma notificação disponível para importação." (template) apareça
            notificationRows.style.display = 'none';
        }
    }
})();
