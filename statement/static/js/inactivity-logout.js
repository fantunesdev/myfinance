(() => {
    const element = document.getElementById('inactivity-logout-config');
    if (!element) return;
    const initial = JSON.parse(element.textContent);
    const prefix = `myfinance:inactivity:${initial.session}:`;
    const root = document.documentElement;
    const memory = new Map();
    let config = initial;
    let locked = false;
    let sending = false;
    const channel = typeof BroadcastChannel === 'function' ? new BroadcastChannel(prefix) : null;

    function read(name) {
        try { return JSON.parse(localStorage.getItem(prefix + name)) ?? memory.get(name); }
        catch { return memory.get(name); }
    }

    function write(name, value) {
        memory.set(name, value);
        try { localStorage.setItem(prefix + name, JSON.stringify(value)); } catch { /* Use the channel when storage is unavailable. */ }
        channel?.postMessage({ name, value });
    }

    function conceal() {
        root.classList.add('myfinance-privacy-hidden');
    }

    function showLock() {
        if (!document.body || document.getElementById('inactivity-screen')) return;
        const screen = document.createElement('div');
        screen.id = 'inactivity-screen';
        screen.setAttribute('role', 'status');
        screen.textContent = 'Você saiu por inatividade. Concluindo a saída…';
        document.body.appendChild(screen);
    }

    async function finishLogout() {
        if (sending || !locked) return;
        sending = true;
        try {
            const response = await fetch(initial.logoutUrl, {
                method: 'POST', credentials: 'same-origin', cache: 'no-store',
                headers: {
                    'X-CSRFToken': document.querySelector('meta[name="myfinance-csrf"]').content,
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({ session: initial.session }),
            });
            if (response.ok || response.status === 409) location.replace(initial.loginUrl);
        } catch { /* Keep financial data concealed and retry once the connection returns. */ }
        finally { sending = false; }
    }

    function expire() {
        if (locked) return;
        locked = true;
        window.myfinanceInactivityExpired = true;
        conceal();
        showLock();
        write('ended', true);
        window.dispatchEvent(new Event('myfinance:inactivity'));
        try {
            for (const key of Object.keys(sessionStorage)) {
                if (key.startsWith('myfinance:investments:')) sessionStorage.removeItem(key);
            }
        } catch { /* The screen remains concealed without access to storage. */ }
        void finishLogout();
    }

    function check() {
        if (locked) return false;
        config = read('config') || config;
        if (read('ended')) { expire(); return false; }
        const last = Math.max(read('activity') || 0, memory.get('activity') || 0);
        if (config.enabled && Date.now() - last >= config.minutes * 60000) {
            expire();
            return false;
        }
        if (!config.enabled || document.visibilityState !== 'hidden') {
            root.classList.remove('myfinance-privacy-hidden');
        }
        return true;
    }

    function activity(event) {
        // Check the old deadline first: a late click cannot revive expired access.
        if (!check()) {
            event.preventDefault();
            event.stopImmediatePropagation();
            return;
        }
        if (!config.enabled || document.visibilityState === 'hidden' || !event.isTrusted) return;
        write('activity', Date.now());
    }

    function receive(name, value) {
        if (name === 'activity') value = Math.max(value || 0, memory.get(name) || 0);
        memory.set(name, value);
        check();
    }

    window.addEventListener('storage', event => {
        if (!event.key?.startsWith(prefix) || event.newValue === null) return;
        try { receive(event.key.slice(prefix.length), JSON.parse(event.newValue)); } catch { /* Ignore malformed entries. */ }
    });
    if (channel) channel.onmessage = event => receive(event.data.name, event.data.value);

    const shared = read('config');
    if (!shared || (initial.revision || '') > (shared.revision || '')) {
        if (shared && (initial.enabled !== shared.enabled || initial.minutes !== shared.minutes)) {
            write('activity', Date.now());
        }
        write('config', initial);
    }
    if (!read('activity')) write('activity', Date.now());

    for (const name of ['pointerdown', 'click', 'keydown', 'wheel', 'touchstart', 'touchmove']) {
        window.addEventListener(name, activity, { capture: true, passive: false });
    }
    document.addEventListener('visibilitychange', () => {
        if (config.enabled && document.visibilityState === 'hidden') conceal();
        check();
    });
    window.addEventListener('pagehide', () => {
        if (config.enabled) conceal();
        if (!locked && memory.get('activity')) write('activity', memory.get('activity'));
    });
    window.addEventListener('pageshow', check);
    window.addEventListener('focus', check);
    window.addEventListener('online', () => { if (!check()) void finishLogout(); });
    document.addEventListener('DOMContentLoaded', () => { if (locked) showLock(); });
    setInterval(() => { if (!check()) void finishLogout(); }, 1000);
    check();
})();
