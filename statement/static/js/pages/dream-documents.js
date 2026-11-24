const add = document.querySelector('[data-document-add]');
const form = document.querySelector('#dream-document-upload');

if (add && form) {
    const input = form.querySelector('input[type=file]');
    const selection = form.querySelector('[data-document-selection]');
    add.addEventListener('click', () => {
        form.hidden = !form.hidden;
        add.setAttribute('aria-expanded', String(!form.hidden));
    });
    input.addEventListener('change', () => {
        const count = input.files.length;
        selection.hidden = count === 0;
        selection.textContent = count === 1 ? '1 documento selecionado' : `${count} documentos selecionados`;
    });
}
