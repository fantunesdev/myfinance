const ACTIVE = new Set(['submitting', 'queued', 'running']);
const labels = {
    submitting: 'Confirmando solicitação…', queued: 'Aguardando execução…',
    loading: 'Carregando dados…', preparing: 'Preparando feedbacks…',
    training: 'Treinando', validating: 'Validando', saving: 'Salvando modelo…',
    completed: 'Concluído', failed: 'Falha no treinamento', interrupted: 'Treinamento interrompido',
};
const jobs = new Map();
const pending = new Map();
const sending = new Set();
const userId = document.querySelector('meta[name="myfinance-user-id"]')?.content;
const storageKey = `myfinance:classifier:pending:${userId}`;
let polling = false;
let timer;

function savePending() {
    try { sessionStorage.setItem(storageKey, JSON.stringify([...pending.values()])); } catch { /* Optional storage. */ }
}

function csrfToken() {
    return document.cookie.split(';').map(value => value.trim()).find(value => value.startsWith('csrftoken='))?.slice(10) || '';
}

function render() {
    for (const [predictor, job] of jobs) {
        const container = document.querySelector(`[data-classifier-progress="${predictor}"]`);
        if (!container) continue;
        const active = ACTIVE.has(job.status);
        container.hidden = false;
        for (const action of ['train', 'feedback']) {
            const button = document.getElementById(`${predictor}-${action}-btn`);
            if (button) button.disabled = active;
        }
        const progress = container.querySelector('progress');
        const text = container.querySelector('[data-classifier-message]');
        const measured = job.total > 0 && ['training', 'preparing', 'validating'].includes(job.stage);
        if (job.status === 'succeeded') progress.value = 100;
        else if (measured) progress.value = Math.min(100, Math.floor(100 * job.completed / job.total));
        else progress.removeAttribute('value');
        progress.hidden = !active && job.status !== 'succeeded';
        let message = labels[job.stage || job.status] || job.status;
        if (job.status === 'succeeded' || ['failed', 'interrupted'].includes(job.status)) {
            message = job.message || message;
        } else if (measured) {
            message += `: ${job.completed} de ${job.total} — ${progress.value}%`;
        }
        const lastSeen = Date.parse(job.heartbeat_at || job.created_at);
        if (active && Date.now() - lastSeen > 30000) {
            message += ' — Sem atualização; verificando execução.';
        }
        text.textContent = message;
        if (job.status === 'succeeded') {
            const status = document.querySelector(`[data-classifier-status="${predictor}"]`);
            if (status) status.textContent = 'Treinado';
        }
    }
    const deleteButton = document.getElementById('delete-feedbacks-btn');
    if (deleteButton) deleteButton.disabled = [...jobs.values()].some(job => ACTIVE.has(job.status));
}

function accept(job, authoritative = false) {
    const current = jobs.get(job.predictor);
    if (current && current.id === job.id && current.revision > job.revision) return;
    if (!authoritative && current && current.id !== job.id && Date.parse(current.created_at) > Date.parse(job.created_at)) return;
    jobs.set(job.predictor, job);
    const request = pending.get(job.predictor);
    if (job.status !== 'submitting' && (request?.id === job.id || (request && ACTIVE.has(job.status)))) {
        pending.delete(job.predictor);
        savePending();
    }
    render();
}

async function submit(request) {
    if (sending.has(request.predictor)) return;
    sending.add(request.predictor);
    const controller = new AbortController();
    const deadline = setTimeout(() => controller.abort(), 15000);
    try {
        const response = await fetch(`/api/${request.route}/`, {
            method: 'POST', signal: controller.signal,
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': decodeURIComponent(csrfToken()),
                'Idempotency-Key': request.id },
        });
        const data = await response.json().catch(() => ({}));
        if (response.ok && data.job) accept(data.job, true);
        else if (response.status >= 400 && response.status < 500 && ![408, 429].includes(response.status)) {
            pending.delete(request.predictor);
            jobs.delete(request.predictor);
            savePending();
            const container = document.querySelector(`[data-classifier-progress="${request.predictor}"]`);
            if (container) container.hidden = true;
            for (const action of ['train', 'feedback']) {
                const button = document.getElementById(`${request.predictor}-${action}-btn`);
                if (button) button.disabled = false;
            }
            const message = [401, 403].includes(response.status)
                ? 'A sessão expirou ou o acesso foi recusado. Recarregue a página e entre novamente, se necessário.'
                : `O servidor recusou a solicitação (HTTP ${response.status}). Recarregue a página e tente novamente.`;
            window.showModal('Solicitação não aceita', data.error || message);
            render();
        }
    } catch {
        // Keep the same identifier: a lost HTTP response is not a failed training.
    } finally {
        clearTimeout(deadline);
        sending.delete(request.predictor);
    }
}

export async function startClassifierJob(route) {
    const predictor = route.split('/')[1];
    if (ACTIVE.has(jobs.get(predictor)?.status)) return;
    const request = { id: crypto.randomUUID(), predictor, route, created_at: new Date().toISOString() };
    pending.set(predictor, request);
    savePending();
    accept({ ...request, operation: route.split('/')[2], status: 'submitting', revision: 0 });
    await submit(request);
}

async function poll() {
    if (polling) return;
    polling = true;
    const controller = new AbortController();
    const deadline = setTimeout(() => controller.abort(), 15000);
    try {
        const response = await fetch('/api/transaction-classifier/jobs/', { signal: controller.signal });
        if (response.ok) {
            const data = await response.json();
            for (const job of data.jobs || []) accept(job);
        }
    } catch { /* Keep displaying the last confirmed state. */ }
    finally {
        clearTimeout(deadline);
        polling = false;
        render();
        for (const request of pending.values()) void submit(request);
    }
}

if (document.querySelector('[data-classifier-progress]')) {
    try {
        for (const request of JSON.parse(sessionStorage.getItem(storageKey) || '[]')) {
            pending.set(request.predictor, request);
            jobs.set(request.predictor, { ...request, status: 'submitting', revision: 0 });
        }
    } catch { /* Optional storage. */ }
    window.addEventListener('classifier:changed', event => accept(event.detail));
    window.addEventListener('pageshow', () => { clearInterval(timer); timer = setInterval(poll, 5000); void poll(); });
    window.addEventListener('pagehide', () => clearInterval(timer));
    render();
    timer = setInterval(poll, 5000);
    void poll();
}
