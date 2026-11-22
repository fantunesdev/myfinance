(() => {
    const allowed = new Set(['B', 'STRONG', 'I', 'EM', 'U', 'S', 'STRIKE', 'P', 'DIV', 'BR', 'UL', 'OL', 'LI', 'BLOCKQUOTE']);
    function cleanNode(node) {
        if (node.nodeType === Node.TEXT_NODE) return document.createTextNode(node.textContent);
        const fragment = document.createDocumentFragment();
        if (node.nodeType !== Node.ELEMENT_NODE || ['SCRIPT', 'STYLE'].includes(node.tagName)) return fragment;
        const result = allowed.has(node.tagName) ? document.createElement(node.tagName.toLowerCase()) : fragment;
        node.childNodes.forEach((child) => result.append(cleanNode(child)));
        return result;
    }

    document.querySelectorAll('[data-rich-text]').forEach((root) => {
        const textarea = root.querySelector('textarea');
        const editor = root.querySelector('[contenteditable]');
        const toolbar = root.querySelector('[role=toolbar]');
        const sourceButton = toolbar.querySelector('[data-source]');
        let sourceMode = false;
        const sync = () => { if (!sourceMode) textarea.value = editor.innerHTML; };
        function cleanHTML(html) {
            const parsed = new DOMParser().parseFromString(html, 'text/html');
            const container = document.createElement('div');
            parsed.body.childNodes.forEach((child) => container.append(cleanNode(child)));
            return container;
        }
        textarea.hidden = true;
        editor.hidden = false;
        toolbar.hidden = false;
        const label = document.querySelector(`label[for="${textarea.id}"]`);
        label?.addEventListener('click', (event) => {
            event.preventDefault();
            (sourceMode ? textarea : editor).focus();
        });
        toolbar.addEventListener('mousedown', (event) => event.preventDefault());
        toolbar.addEventListener('click', (event) => {
            if (event.target.closest('[data-source]')) {
                sync();
                sourceMode = !sourceMode;
                if (!sourceMode) editor.replaceChildren(...cleanHTML(textarea.value).childNodes);
                editor.hidden = sourceMode;
                textarea.hidden = !sourceMode;
                sourceButton.setAttribute('aria-pressed', String(sourceMode));
                toolbar.querySelectorAll('[data-command]').forEach((button) => { button.disabled = sourceMode; });
                (sourceMode ? textarea : editor).focus();
                return;
            }
            const button = event.target.closest('[data-command]');
            if (!button) return;
            editor.focus();
            document.execCommand(button.dataset.command, false);
            sync();
        });
        editor.addEventListener('input', sync);
        editor.addEventListener('paste', (event) => {
            event.preventDefault();
            const html = event.clipboardData.getData('text/html');
            if (html) {
                const container = cleanHTML(html);
                document.execCommand('insertHTML', false, container.innerHTML);
            } else {
                document.execCommand('insertText', false, event.clipboardData.getData('text/plain'));
            }
            sync();
        });
        editor.addEventListener('drop', (event) => event.preventDefault());
        textarea.form.addEventListener('submit', sync);
    });
})();
