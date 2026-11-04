/**
 * Gerenciador de seleção de tipo de importação (arquivo ou notificações)
 * Mostra/esconde as seções conforme a escolha do usuário
 */

// Elementos do DOM
const importTypeFile = document.querySelector('#import-type-file');
const importTypeNotifications = document.querySelector('#import-type-notifications');
const sectionFileImport = document.querySelector('#section-file-import');
const sectionNotificationsImport = document.querySelector('#section-notifications-import');
const sectionPluggyImport = document.querySelector('#section-pluggy-import');

function selectImportSource() {
    const value = document.querySelector('input[name="import-type"]:checked')?.value;
    [[sectionFileImport, 'file'], [sectionNotificationsImport, 'notifications'], [sectionPluggyImport, 'pluggy']].forEach(([section, type]) => {
        if (!section) return;
        section.classList.toggle('toggled', value !== type);
        section.style.display = value === type ? '' : 'none';
    });
}
document.querySelectorAll('input[name="import-type"]').forEach((radio) => {
    radio.addEventListener('change', selectImportSource);
});
selectImportSource();
const fileTypeConfigurableCSV = document.querySelector('#file-type-configurable-csv');
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

if (fileTypeConfigurableCSV) {
    fileTypeConfigurableCSV.addEventListener('change', () => {
        if (sectionFileTitle) sectionFileTitle.textContent = 'Importar CSV configurável';
    });
}

if (fileTypeTasker) {
    fileTypeTasker.addEventListener('change', () => {
        if (sectionFileTitle) sectionFileTitle.textContent = 'Importar Notificações';
    });
}
