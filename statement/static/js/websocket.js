(() => {
    const userId = document.querySelector('meta[name="myfinance-user-id"]')?.content;
    if (!userId) return;
    const prefix = `myfinance:investments:v1:${userId}:`;
    let stopped = false;
    let reconnectTimer;
    let retry = 1000;

    function invalidate(revision) {
        try {
            const cached = JSON.parse(sessionStorage.getItem(`${prefix}data`) || 'null');
            if (cached && revision && cached.data.revision === revision) return;
            sessionStorage.setItem(`${prefix}changed`, JSON.stringify({ revision, at: Date.now() }));
        } catch { /* The active dashboard can still refresh without storage. */ }
        window.dispatchEvent(new CustomEvent('investments:changed', { detail: { revision } }));
    }

    window.addEventListener('investments:mutation', () => invalidate(null));
    document.addEventListener('submit', event => {
        const form = event.target;
        if (form.method?.toLowerCase() !== 'post') return;
        const path = new URL(form.action || location.href, location.href).pathname;
        if (path.startsWith('/investimentos/') || path.startsWith('/relatorio_financeiro/')) invalidate(null);
    });

    function connect() {
        if (stopped || [WebSocket.OPEN, WebSocket.CONNECTING].includes(window.socket?.readyState)) return;
        clearTimeout(reconnectTimer);
        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const socket = new WebSocket(`${protocol}//${location.host}/ws/`);
        window.socket = socket;
        socket.onopen = () => { retry = 1000; };
        socket.onmessage = event => {
            try {
                const message = JSON.parse(event.data);
                if (message.type === 'classifier.changed') {
                    window.dispatchEvent(new CustomEvent('classifier:changed', { detail: message.job }));
                } else if (['investments.changed', 'investments.ready'].includes(message.type)) {
                    invalidate(message.revision);
                } else if (message.data) {
                    for (const [key, value] of Object.entries(message.data)) {
                        try { sessionStorage.setItem(key, JSON.stringify(value)); } catch { /* Storage unavailable. */ }
                    }
                }
            } catch (error) {
                console.error('Mensagem WebSocket inválida:', error);
            }
        };
        socket.onclose = event => {
            if (socket !== window.socket || stopped) return;
            if (event.code === 4401) { stopped = true; return; }
            reconnectTimer = setTimeout(connect, retry + Math.random() * 200);
            retry = Math.min(retry * 2, 30000);
        };
        socket.onerror = () => { socket.close(); };
    }

    document.addEventListener('click', event => {
        if (!event.target.closest?.('[data-clear-investments-cache]')) return;
        stopped = true;
        clearTimeout(reconnectTimer);
        window.socket?.close();
        try {
            for (const key of Object.keys(sessionStorage)) {
                if (key.startsWith('myfinance:investments:v1:')) sessionStorage.removeItem(key);
            }
        } catch { /* Storage unavailable. */ }
    });
    window.addEventListener('pagehide', () => {
        stopped = true;
        clearTimeout(reconnectTimer);
        window.socket?.close();
    });
    window.addEventListener('pageshow', () => { stopped = false; connect(); });
    connect();
})();
