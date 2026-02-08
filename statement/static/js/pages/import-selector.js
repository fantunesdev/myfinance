/**
 * Gerenciador de seleção de tipo de importação (arquivo ou notificações)
 * Mostra/esconde as seções conforme a escolha do usuário
 */

// Elementos do DOM
const importTypeFile = document.querySelector('#import-type-file');
const importTypeNotifications = document.querySelector('#import-type-notifications');
const sectionFileImport = document.querySelector('#section-file-import');
const sectionNotificationsImport = document.querySelector('#section-notifications-import');

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
