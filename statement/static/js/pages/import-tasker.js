/**
 * Importação de notificações via JSON Tasker
 * Manipula o upload, processamento e cadastro de notificações do Tasker
 */

import * as services from '../data/services.js';

// Elementos DOM
const fileTypeCSV = document.querySelector('#file-type-csv');
const fileTypeTasker = document.querySelector('#file-type-tasker');
const formCSV = document.querySelector('#form-csv');
const formTasker = document.querySelector('#form-tasker');
const fileTaskerInput = document.querySelector('#id_file_tasker');
const importTaskerBtn = document.querySelector('#import-tasker-btn');

/**
 * Alterna entre os formulários CSV e Tasker
 */
function toggleFileType() {
    const isCSV = fileTypeCSV.checked;
    
    if (isCSV) {
        formCSV.classList.remove('toggled');
        formTasker.classList.add('toggled');
    } else {
        formCSV.classList.add('toggled');
        formTasker.classList.remove('toggled');
    }
}

/**
 * Processa o arquivo JSON do Tasker
 */
async function importTaskerJSON() {
    const file = fileTaskerInput.files[0];
    const importError = document.querySelector('#import-error');
    
    if (!file) {
        alert('Selecione um arquivo Tasker JSON para continuar.');
        return;
    }
    
    // Lê o arquivo
    const fileContent = await file.text();
    
    // Parseia e valida os JSONs
    const notifications = [];
    const errors = [];
    
    for (let lineNum = 0; lineNum < fileContent.split('\n').length; lineNum++) {
        const line = fileContent.split('\n')[lineNum];
        
        if (!line.trim()) continue;
        
        try {
            const data = JSON.parse(line);
            
            // Valida campos obrigatórios
            if (!data.app || !data.title || !data.message || !data.date) {
                errors.push(`Linha ${lineNum + 1}: Faltam campos obrigatórios (app, title, message, date)`);
                continue;
            }
            
            notifications.push(data);
        } catch (e) {
            errors.push(`Linha ${lineNum + 1}: JSON inválido - ${e.message}`);
        }
    }
    
    if (errors.length > 0) {
        importError.classList.remove('toggled');
        importError.textContent = 'Erros encontrados:\n' + errors.join('\n');
        return;
    }
    
    if (notifications.length === 0) {
        alert('Nenhuma notificação válida encontrada no arquivo.');
        return;
    }
    
    // Envia para o backend via FormData (assim como CSV)
    const formData = new FormData();
    formData.append('file', file);
    formData.append('import_type', 'tasker_json');
    formData.append('account', '');
    formData.append('card', document.querySelector('#id_card_tasker').value || '');
    
    try {
        const response = await fetch('/api/transactions/import/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: formData,
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.errors || 'Erro ao processar arquivo');
        }
        
        const processedNotifications = await response.json();
        
        // Renderiza as notificações processadas
        await renderNotifications(processedNotifications);
        importError.classList.add('toggled');
    } catch (error) {
        importError.classList.remove('toggled');
        importError.textContent = `Erro ao processar arquivo: ${error.message}`;
    }
}

/**
 * Renderiza as notificações em uma tabela
 */
async function renderNotifications(notifications) {
    const notificationRows = document.querySelector('#notification-rows-tasker');
    const boxNotifications = document.querySelector('#box-notifications');
    const categories = await services.getCategoriesByType('saida');
    
    notificationRows.innerHTML = '';
    
    for (let i = 0; i < notifications.length; i++) {
        const notification = notifications[i];
        const row = document.createElement('tr');
        const subcategories = [];
        
        const fields = [
            {
                type: 'checkbox',
                id: `tasker_${notification.app}_${notification.message.substring(0, 20)}`,
                render: (cell) => {
                    const checkbox = document.createElement('input');
                    checkbox.type = 'checkbox';
                    checkbox.dataset.notification = JSON.stringify(notification);
                    checkbox.addEventListener('change', function() {
                        row.classList.toggle('row-disabled', !this.checked);
                    });
                    cell.appendChild(checkbox);
                }
            },
            {
                id: `id_date_tasker_${i}`,
                type: 'text',
                value: notification.date.split(' ')[0],
            },
            {
                id: `id_category_tasker_${i}`,
                type: 'select',
                options: categories,
                selected: notification.category || null,
                onChange: async (selectElem, cell) => {
                    const subcategorySelect = cell.nextSibling.querySelector('select');
                    const subcategories = await services.getChildrenResource('categories', 'subcategories', selectElem.value);
                    updateSelectOptions(subcategorySelect, subcategories);
                },
            },
            {
                id: `id_subcategory_tasker_${i}`,
                type: 'select',
                options: subcategories,
                selected: notification.subcategory || null,
            },
            {
                type: 'text',
                value: notification.message.substring(0, 100),
                title: notification.message,
            },
            {
                type: 'text',
                value: extractValue(notification.message),
                disabled: true,
            },
        ];
        
        renderFields(row, fields);
        notificationRows.appendChild(row);
        // Popula o select de subcategorias baseado na categoria atualmente selecionada
        const categorySelect = document.getElementById(`id_category_tasker_${i}`);
        const subSel = document.getElementById(`id_subcategory_tasker_${i}`);
        if (categorySelect && subSel) {
            const selectedCategory = categorySelect.value;
            if (selectedCategory && parseInt(selectedCategory, 10) > 0) {
                const subcats = await services.getChildrenResource('categories', 'subcategories', selectedCategory);
                updateSelectOptions(subSel, subcats);
                if (notification.subcategory) subSel.value = notification.subcategory;
            }
        }
    }
    
    // Mostra a tabela de notificações
    if (boxNotifications) {
        boxNotifications.classList.remove('toggled');
    }
}

/**
 * Renderiza os campos em uma linha da tabela
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
        // Ajusta largura da célula para valor/descrição garantindo layout
        if (field.id && field.id.startsWith('id_value_')) {
            cell.style.width = '140px';
            cell.style.whiteSpace = 'nowrap';
        } else if (field.id && field.id.startsWith('id_description_')) {
            cell.style.width = 'auto';
        }

        cell.appendChild(element);
    });
}

/**
 * Cria um elemento input
 */
function createInput(field) {
    const input = document.createElement('input');
    input.type = field.type || 'text';
    if (field.title) input.title = field.title;
    if (input.type === 'date') {
        input.value = formatDateForInput(field.value || '');
    } else {
        input.value = field.value || '';
    }
    input.classList.add('form-control');
    // Ajustes de tamanho e limites para campos de valor e descrição
    if (field.id && field.id.startsWith('id_value_')) {
        input.maxLength = 9;
        input.pattern = '^[0-9]{1,6}(\\.[0-9]{2})?$';
        input.style.setProperty('width', '120px', 'important');
        input.style.setProperty('max-width', '120px', 'important');
        input.style.setProperty('display', 'inline-block', 'important');
        input.style.textAlign = 'right';
    }
    if (field.id && field.id.startsWith('id_description_')) {
        input.maxLength = 255;
        input.style.setProperty('width', 'auto', 'important');
        input.style.setProperty('min-width', '200px', 'important');
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
 * Cria um elemento select
 */
function createSelect(field) {
    const select = document.createElement('select');
    if (field.id) select.id = field.id;
    select.classList.add('form-control');
    
    // default empty option
    const defaultOpt = document.createElement('option');
    defaultOpt.value = 0;
    defaultOpt.textContent = '---------';
    select.appendChild(defaultOpt);

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
 * Atualiza as options de um select com uma lista de options.
 * @param {HTMLSelectElement} select
 * @param {Array} options
 */
function updateSelectOptions(select, options) {
    if (!select) return;
    select.innerHTML = '';
    const defaultOpt = document.createElement('option');
    defaultOpt.value = 0;
    defaultOpt.textContent = '---------';
    select.appendChild(defaultOpt);
    options.forEach((opt) => {
        const option = document.createElement('option');
        option.value = opt.id;
        option.textContent = opt.description;
        select.appendChild(option);
    });
}

/**
 * Extrai o valor monetário da mensagem
 */
function extractValue(message) {
    const match = message.match(/R\$\s*([\d.,]+)/);
    if (match) {
        return match[1];
    }
    return '';
}

/**
 * Obtém o valor de um cookie pelo nome
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

// Event listeners
if (fileTypeCSV && fileTypeTasker) {
    fileTypeCSV.addEventListener('change', toggleFileType);
    fileTypeTasker.addEventListener('change', toggleFileType);
}

if (importTaskerBtn) {
    importTaskerBtn.addEventListener('click', importTaskerJSON);
}

// Select all checkbox para Tasker
const checkallTasker = document.querySelector('#checkall-tasker');
const notificationRowsTasker = document.querySelector('#notification-rows-tasker');

if (checkallTasker && notificationRowsTasker) {
    checkallTasker.addEventListener('change', function() {
        for (const row of notificationRowsTasker.children) {
            const checkbox = row.children[0].children[0];
            checkbox.checked = this.checked;
            row.classList.toggle('row-disabled', !this.checked);
        }
    });
}

// Salvar notificações Tasker
const saveTaskerBtn = document.querySelector('#save-tasker-notifications-btn');

if (saveTaskerBtn) {
    saveTaskerBtn.addEventListener('click', async () => {
        const selectedNotifications = [];
        const card = document.querySelector('#id_card_tasker').value;
        
        if (!notificationRowsTasker) return;
        
        // Coleta as notificações selecionadas
        for (const row of notificationRowsTasker.children) {
            const checkbox = row.children[0].children[0];
            if (checkbox.checked && checkbox.dataset.notification) {
                const notification = JSON.parse(checkbox.dataset.notification);
                notification.card = card !== 'tasker' ? card : null;
                selectedNotifications.push(notification);
            }
        }
        
        if (selectedNotifications.length === 0) {
            alert('Selecione pelo menos uma notificação para cadastrar.');
            return;
        }
        
        // Salva as notificações via API
        await saveNotifications(selectedNotifications);
    });
}

/**
 * Salva as notificações processadas no backend
 */
async function saveNotifications(notifications) {
    const importError = document.querySelector('#import-error');
    
    try {
        for (const notification of notifications) {
            const response = await fetch('/api/notifications/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                },
                body: JSON.stringify({
                    app: notification.app,
                    title: notification.title,
                    message: notification.message,
                    is_used: false,
                    // Preserve original notification date/time when available
                    created_at: notification.date || notification.datetime || null,
                }),
            });
            
            if (!response.ok) {
                throw new Error(`Erro ao salvar notificação: ${response.statusText}`);
            }
        }
        
        importError.classList.remove('toggled');
        importError.textContent = `${notifications.length} notificação(ões) salva(s) com sucesso!`;
        
        // Limpa a tabela e reset
        setTimeout(() => {
            notificationRowsTasker.innerHTML = '';
            document.querySelector('#box-notifications').classList.add('toggled');
            document.querySelector('#id_file_tasker').value = '';
            fileTypeCSV.checked = true;
            toggleFileType();
        }, 2000);
    } catch (error) {
        importError.classList.remove('toggled');
        importError.textContent = `Erro ao salvar notificações: ${error.message}`;
    }
}
