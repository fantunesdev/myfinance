(() => {
    'use strict';
    const stack = document.getElementById('flash-toasts');
    if (!stack) return;
    const active = new Set();
    const duration = 20000;

    function attach(element) {
        let remaining = duration;
        let started = 0;
        let timer;
        let hovering = false;
        let focused = false;
        const entry = { update, close };
        active.add(entry);
        while (active.size > 3) active.values().next().value.close();
        function close() {
            clearTimeout(timer);
            active.delete(entry);
            element.remove();
        }
        function update() {
            if (timer !== undefined) {
                clearTimeout(timer);
                remaining = Math.max(0, remaining - (Date.now() - started));
                timer = undefined;
            }
            if (!hovering && !focused && !document.hidden) {
                started = Date.now();
                timer = setTimeout(close, remaining);
            }
        }
        element.querySelector('.toast-close').addEventListener('click', close);
        element.addEventListener('pointerenter', () => { hovering = true; update(); });
        element.addEventListener('pointerleave', () => { hovering = false; update(); });
        element.addEventListener('focusin', () => { focused = true; update(); });
        element.addEventListener('focusout', event => {
            focused = element.contains(event.relatedTarget);
            update();
        });
        update();
    }
    stack.querySelectorAll('.app-toast').forEach(attach);
    document.addEventListener('visibilitychange', () => active.forEach(entry => entry.update()));

    // Text is inserted as textContent, including messages from clipboard actions.
    window.myFinanceToast = (message, level = 'info') => {
        const titles = { success: 'Tudo certo', error: 'Não foi possível concluir', warning: 'Atenção', info: 'Informação' };
        if (!Object.hasOwn(titles, level)) level = 'info';
        const element = document.createElement('div');
        element.className = 'app-toast';
        element.dataset.toastLevel = level;
        element.setAttribute('role', level === 'error' ? 'alert' : 'status');
        const symbol = document.createElement('span');
        symbol.className = 'toast-symbol';
        symbol.setAttribute('aria-hidden', 'true');
        symbol.textContent = { success: '✓', error: '!', warning: '!', info: 'i' }[level];
        const content = document.createElement('div');
        content.className = 'toast-content';
        const title = document.createElement('strong');
        title.textContent = titles[level];
        const text = document.createElement('p');
        text.textContent = message;
        content.append(title, text);
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'toast-close';
        button.setAttribute('aria-label', 'Fechar notificação');
        button.textContent = '×';
        element.append(symbol, content, button);
        stack.append(element);
        attach(element);
    };
})();
