(() => {
    'use strict';
    const dialog = document.getElementById('profile-dialog');
    if (!dialog || !window.fetch || !dialog.showModal) return;
    const content = document.getElementById('profile-dialog-content');
    const title = document.getElementById('profile-dialog-title');
    const closeButton = dialog.querySelector('[data-profile-close]');
    const stack = document.getElementById('flash-toasts');
    const homeUrl = new URL(location.href);
    let currentUrl = homeUrl;
    let busy = false;
    let loading;
    let opener;
    const pendingForms = new WeakSet();
    const globalSettings = dialog.hasAttribute?.('data-global-settings-dialog') === true;
    let customTitle = '';
    const defaultTitle = globalSettings ? 'Configurações globais' : 'Configurações da conta';

    function notify(message, level = 'info') {
        window.myFinanceToast(message, level);
    }
    function localUrl(value, base = currentUrl) {
        const url = new URL(value, base);
        if (url.origin !== location.origin || !['http:', 'https:'].includes(url.protocol)) {
            throw new Error('Não foi possível abrir este endereço no formulário.');
        }
        return url;
    }
    function isOAuth(url) { return url.pathname.startsWith('/auth/login/'); }
    function busyState(value) {
        busy = value;
        closeButton.disabled = value;
        content.setAttribute('aria-busy', String(value));
    }
    function close() {
        if (busy) return;
        loading?.abort();
        dialog.close();
    }
    dialog.addEventListener('cancel', event => { event.preventDefault(); close(); });
    closeButton.addEventListener('click', close);
    dialog.addEventListener('close', () => {
        loading?.abort();
        document.body.classList.remove('profile-dialog-open');
        if (stack) document.body.append(stack);
        content.replaceChildren(); // Clear passwords, authenticator secrets and recovery codes.
        if (opener?.isConnected) opener.focus();
        else [...document.querySelectorAll('main [data-profile-modal]')].find(link => link.href === opener?.href)?.focus();
    });

    async function readPage(response) {
        const url = localUrl(response.url);
        if (/^\/login\/?$/.test(url.pathname)) {
            throw new Error('Sua sessão expirou. Entre novamente para continuar.');
        }
        if (!response.ok) {
            const message = response.status === 403
                ? 'Acesso recusado ou sessão de segurança expirada. Atualize a página antes de tentar novamente.'
                : `Não foi possível concluir a solicitação (HTTP ${response.status}).`;
            throw new Error(message);
        }
        if (!response.headers.get('Content-Type')?.includes('text/html')) {
            throw new Error('O servidor retornou uma resposta inesperada.');
        }
        const page = new DOMParser().parseFromString(await response.text(), 'text/html');
        return { page, url };
    }
    function feedback(page) {
        const messages = [...page.querySelectorAll('#flash-toasts .app-toast')];
        for (const message of messages) {
            notify(message.querySelector('.toast-content p')?.textContent || 'Verifique a solicitação.', message.dataset.toastLevel);
        }
        return { any: messages.length > 0, failed: messages.some(message => ['error', 'warning'].includes(message.dataset.toastLevel)) };
    }
    function fragment(page, url) {
        const root = page.querySelector('main') || page.querySelector('body > .box');
        if (!root) throw new Error('Não foi possível carregar este formulário.');
        const copy = root.cloneNode(true);
        // Scripts are initialized explicitly; never execute code from fetched markup.
        copy.querySelectorAll('script, link, #flash-toasts, #profile-dialog').forEach(node => node.remove());
        for (const form of copy.querySelectorAll('form')) {
            form.setAttribute('action', localUrl(form.getAttribute('action') || url.href, url).href);
        }
        for (const link of copy.querySelectorAll('a[href]')) {
            const href = link.getAttribute('href');
            if (href.startsWith('#')) continue;
            link.href = localUrl(href, url).href;
            if (link.textContent.trim() === 'Voltar') {
                link.removeAttribute('href');
                link.setAttribute('data-profile-close', '');
                link.setAttribute('role', 'button');
                link.tabIndex = 0;
            }
        }
        if (root.matches('.box')) {
            const wrapper = document.createElement('div');
            wrapper.append(copy);
            return wrapper;
        }
        return copy;
    }
    function ensureOpen(trigger = document.activeElement) {
        if (!dialog.open) {
            opener = trigger;
            dialog.showModal();
            document.body.classList.add('profile-dialog-open');
            if (stack) dialog.append(stack); // Toasts stay above the native dialog's backdrop.
        }
    }
    function render(page, url, focusErrors = false) {
        ensureOpen();
        const copy = fragment(page, url);
        currentUrl = url;
        title.textContent = customTitle || page.querySelector('main .box-title, body > .box .box-title, main h2')?.textContent.trim() || defaultTitle;
        content.replaceChildren(...copy.childNodes);
        const classifierLabel = content.querySelector('label[for="id_enable_transaction_classifier"]');
        if (globalSettings && classifierLabel) classifierLabel.textContent = 'Ativar Transaction Classifier';
        content.scrollTop = 0;
        window.initializeCardForm?.(content);
        window.initializeChartPreferences?.(content);
        const firstError = content.querySelector('.errorlist, .alert-danger');
        if (focusErrors && firstError) {
            firstError.tabIndex = -1;
            firstError.focus();
        } else {
            content.querySelector('input:not([type=hidden]):not([type=checkbox]), select, textarea, button, a[href]')?.focus();
        }
    }
    async function open(url, trigger) {
        if (busy) return;
        loading?.abort();
        const controller = new AbortController();
        loading = controller;
        ensureOpen(trigger);
        customTitle = trigger?.dataset?.modalTitle || '';
        title.textContent = 'Carregando…';
        content.textContent = 'Carregando formulário…';
        content.setAttribute('aria-busy', 'true');
        try {
            const { page, url: destination } = await readPage(await fetch(url, {
                credentials: 'same-origin', signal: controller.signal, headers: { 'X-Requested-With': 'XMLHttpRequest' },
            }));
            if (controller.signal.aborted) return;
            feedback(page);
            render(page, destination);
        } catch (error) {
            if (error.name === 'AbortError') return;
            content.textContent = 'Não foi possível carregar o formulário. Feche e tente novamente.';
            notify(error.message || 'Falha de conexão ao carregar o formulário.', 'error');
        } finally {
            if (loading === controller) content.setAttribute('aria-busy', 'false');
        }
    }
    async function refresh(page, url) {
        let replacement = url.pathname === homeUrl.pathname && !url.search ? page.querySelector('.profile-shell') : null;
        if (!replacement) {
            const result = await readPage(await fetch(homeUrl, { credentials: 'same-origin', cache: 'no-store' }));
            page = result.page;
            replacement = page.querySelector('.profile-shell');
        }
        const existing = document.querySelector('main > .profile-shell');
        if (!replacement || !existing) throw new Error('A alteração foi enviada, mas não foi possível atualizar os dados. Atualize a página para conferir.');
        const openSections = [...existing.querySelectorAll('details[open] summary strong')].map(node => node.textContent);
        for (const section of replacement.querySelectorAll('details')) {
            section.open = openSections.includes(section.querySelector('summary strong')?.textContent);
        }
        existing.replaceWith(replacement);
        const settings = page.getElementById('inactivity-logout-config');
        if (settings) window.dispatchEvent(new CustomEvent('profile:inactivity-settings', { detail: JSON.parse(settings.textContent) }));
        // Photo and display name also appear in the navigation bar.
        const headerPhoto = page.getElementById('profile-photo');
        if (headerPhoto) document.getElementById('profile-photo')?.replaceWith(headerPhoto);
        const csrf = page.querySelector('meta[name="myfinance-csrf"]');
        if (csrf) document.querySelector('meta[name="myfinance-csrf"]')?.setAttribute('content', csrf.content);
        window.dispatchEvent(new CustomEvent('profile:updated'));
    }
    document.addEventListener('click', event => {
        if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        const closeTrigger = event.target.closest('[data-profile-close]');
        if (closeTrigger && dialog.contains(closeTrigger)) { event.preventDefault(); close(); return; }
        const link = event.target.closest('a[href]');
        if (!link || (!link.hasAttribute('data-profile-modal') && !content.contains(link))) return;
        if (link.getAttribute('href').startsWith('#') || link.target === '_blank' || link.hasAttribute('download')) return;
        let url;
        try { url = localUrl(link.href); } catch { return; }
        if (isOAuth(url) || url.pathname === '/logout/' || url.pathname === '/login/') return;
        event.preventDefault();
        if (url.pathname === homeUrl.pathname && !url.search) close();
        else void open(url, link);
    });
    dialog.addEventListener('keydown', event => {
        if (event.key === 'Enter' && event.target.matches('a[data-profile-close]')) { event.preventDefault(); close(); }
    });
    window.addEventListener('myfinance:inactivity', () => {
        busyState(false);
        close();
    });
    document.addEventListener('submit', async event => {
        const form = event.target;
        if (!form.matches('form') || (!content.contains(form) && !form.hasAttribute('data-profile-async'))) return;
        const url = localUrl(event.submitter?.getAttribute('formaction') || form.getAttribute('action') || (content.contains(form) ? currentUrl : homeUrl).href);
        if (isOAuth(url)) return; // Google authorization must navigate to Google's consent page.
        event.preventDefault();
        if (busy || pendingForms.has(form)) return;
        const method = (form.getAttribute('method') || 'get').toUpperCase();
        if (method === 'GET') {
            const params = new URLSearchParams(new FormData(form));
            url.search = params.toString();
            void open(url, form);
            return;
        }
        // Native and formset submit listeners have already run before this document listener.
        const data = new FormData(form);
        if (event.submitter?.name) data.append(event.submitter.name, event.submitter.value);
        const buttons = [...form.querySelectorAll('button[type=submit], input[type=submit], button:not([type])')];
        const disabled = buttons.map(button => button.disabled);
        buttons.forEach(button => { button.disabled = true; });
        pendingForms.add(form);
        busyState(true);
        let saved = false;
        try {
            const response = await fetch(url, {
                method, body: data, credentials: 'same-origin',
                headers: { 'X-CSRFToken': data.get('csrfmiddlewaretoken') || '', 'X-Requested-With': 'XMLHttpRequest' },
            });
            const { page, url: destination } = await readPage(response);
            const messages = feedback(page);
            const invalid = page.querySelector('.errorlist, .alert-danger');
            const shell = page.querySelector('.profile-shell');
            if (invalid) {
                if (content.contains(form)) render(page, destination, true);
                if (!messages.failed) notify('Revise os campos destacados. As alterações não foram salvas.', 'error');
            } else if (shell) {
                saved = !messages.failed;
                if (!messages.any) notify(url.pathname.includes('confirmar-identidade') ? 'Identidade confirmada. Confira e confirme a alteração desejada.' : 'Alterações salvas com sucesso.', 'success');
                await refresh(page, destination);
                if (dialog.open && !messages.failed) { busyState(false); close(); }
                else if (dialog.open) render(page, destination);
            } else if (response.redirected && page.querySelector('main table') && !page.querySelector('main form')) {
                saved = !messages.failed;
                if (!messages.any) notify(url.pathname.includes('confirmar-identidade') ? 'Identidade confirmada. Confira e confirme a alteração desejada.' : 'Alterações salvas com sucesso.', 'success');
                await refresh(page, destination);
                if (dialog.open && globalSettings && !messages.failed) { busyState(false); close(); }
                else if (dialog.open) render(page, destination);
            } else {
                // Identity confirmation, QR enrollment and recovery codes remain in the modal.
                render(page, destination);
                const recoveryCodes = content.querySelector('li code');
                if (recoveryCodes) {
                    saved = true;
                    if (!messages.any) notify('Alteração concluída. Guarde seus códigos de recuperação.', 'success');
                    await refresh(page, destination);
                } else if (destination.pathname.includes('confirmar-identidade')) {
                    if (!messages.any) notify('Confirme sua identidade para continuar.', 'info');
                } else if (destination.pathname === url.pathname && !messages.any && !destination.pathname.includes('/2fa/configurar/')) {
                    notify('O formulário continua aberto. Confira os dados antes de confirmar novamente.', 'warning');
                }
            }
        } catch (error) {
            notify(saved ? 'Alteração salva. Não foi possível atualizar a tela; atualize a página para conferir.' :
                (error.message || 'Falha de conexão. A resposta não foi recebida; confira os dados antes de tentar novamente.'), saved ? 'warning' : 'error');
        } finally {
            busyState(false);
            pendingForms.delete(form);
            buttons.forEach((button, index) => { button.disabled = disabled[index]; });
        }
    });
})();
