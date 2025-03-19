const DEBUG = true

if (DEBUG) {
    console.log('Script carregado.');
}

function connectWebSocket() {
    const wsProtocol = window.location.protocol === "https:" ? "wss://" : "ws://";
    const wsHost = window.location.hostname;
    const wsPort = wsHost === 'localhost' ? "8765" : '';
    const wsEndpoint = "/ws/";
    
    if (DEBUG) {
        console.log('Chamando connectWebSocket()...');
    }

    if (window.socket && window.socket.readyState === WebSocket.OPEN) {
        console.log('WebSocket já está conectado.');
        return;
    }

    window.socket = new WebSocket(`${wsProtocol}${wsHost}:${wsPort}${wsEndpoint}`);

    if (DEBUG) {
        console.log('WebSocket criado:', window.socket);
    }

    window.socket.onopen = function () {
        if (DEBUG) {
            console.log('WebSocket conectado.');
        }
    };

    window.socket.onmessage = function (event) {
        if (DEBUG) {
            console.log('Mensagem recebida.');
        }
        
        try {
            const data = JSON.parse(event.data);
            
            if (data.data) {
                const [key, value] = Object.entries(data.data)[0];
    
                sessionStorage.setItem(key, JSON.stringify(value))
                if (DEBUG) {
                    console.log(`Atualizando sessionStorage para ${key}`);
                }
            } else {
                console.warn('Mensagem WebSocket sem dados válidos:', data);
            }
        } catch (error) {
            console.error('Erro ao processar mensagem WebSocket:', error);
        }
    };

    window.socket.onclose = function () {
        if (DEBUG) {
            console.log('WebSocket desconectado.');
        }
    };

    window.socket.onerror = function (error) {
        /** @todo remover debuuging */
        console.error('Erro no WebSocket:', error);
    };
}

connectWebSocket();

if (DEBUG) {
    setTimeout(() => {
        console.log('Após 3 segundos:', window.socket);
    }, 3000);
}
