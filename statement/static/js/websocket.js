/** @todo remover debuuging */
console.log('Script carregado.');

function connectWebSocket() {
    /** @todo remover debuuging */
    console.log('Chamando connectWebSocket()...');

    if (window.socket && window.socket.readyState === WebSocket.OPEN) {
        console.log('WebSocket já está conectado.');
        return;
    }

    window.socket = new WebSocket('ws://localhost:8765/ws/');
    /** @todo remover debuuging */
    console.log('WebSocket criado:', window.socket);

    window.socket.onopen = function () {
        /** @todo remover debuuging */
        console.log('WebSocket conectado.');
    };

    window.socket.onmessage = function (event) {
        /** @todo remover debuuging */
        console.log('Mensagem recebida.');
        
        try {
            const data = JSON.parse(event.data);
            
            if (data.data) {
                const [key, value] = Object.entries(data.data)[0];
    
                sessionStorage.setItem(key, JSON.stringify(value))
                /** @todo remover debuuging */
                console.log(`Atualizando sessionStorage para ${key}`);
            } else {
                console.warn('Mensagem WebSocket sem dados válidos:', data);
            }
        } catch (error) {
            console.error('Erro ao processar mensagem WebSocket:', error);
        }
    };

    window.socket.onclose = function () {
        /** @todo remover debuuging */
        console.log('WebSocket desconectado.');
    };

    window.socket.onerror = function (error) {
        /** @todo remover debuuging */
        console.error('Erro no WebSocket:', error);
    };
}

connectWebSocket();

/** @todo remover debuuging */
// Testando se o WebSocket foi criado corretamente após 3 segundos
setTimeout(() => {
    console.log('Após 3 segundos:', window.socket);
}, 3000);
