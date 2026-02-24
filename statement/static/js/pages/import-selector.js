/**
 * Gerenciador de seleção de tipo de importação (arquivo ou notificações)
 * Mostra/esconde as seções conforme a escolha do usuário
 */

// Elementos do DOM
const importTypeFile = document.querySelector('#import-type-file');
const importTypeNotifications = document.querySelector('#import-type-notifications');
const sectionFileImport = document.querySelector('#section-file-import');
const sectionNotificationsImport = document.querySelector('#section-notifications-import');
const fileTypeCSV = document.querySelector('#file-type-csv');
const fileTypeTasker = document.querySelector('#file-type-tasker');
const sectionFileTitle = sectionFileImport ? sectionFileImport.querySelector('.box-header .box-title') : null;

if (importTypeFile) {
    importTypeFile.addEventListener('change', () => {
        sectionFileImport.classList.remove('toggled');
        if (sectionNotificationsImport) {
            sectionNotificationsImport.classList.add('toggled');
        }
    });
}

if (importTypeNotifications) {
    importTypeNotifications.addEventListener('change', () => {
        sectionFileImport.classList.add('toggled');
        sectionNotificationsImport.classList.remove('toggled');
    });
}

// Atualiza o título do bloco de importação conforme o subtipo de arquivo selecionado
if (fileTypeCSV) {
    fileTypeCSV.addEventListener('change', () => {
        if (sectionFileTitle) sectionFileTitle.textContent = 'Importar Lançamentos por Arquivo';
    });
}

if (fileTypeTasker) {
    fileTypeTasker.addEventListener('change', () => {
        if (sectionFileTitle) sectionFileTitle.textContent = 'Importar Notificações';
    });
}
