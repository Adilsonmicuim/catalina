const logContainer = document.getElementById("log-container");

function connectWebSocket() {
    // Descobre o protocolo correto (ws:// ou wss://)
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/logs`;

    let ws;

    try {
        ws = new WebSocket(wsUrl);
    } catch (err) {
        // Pode acontecer de o navegador nem aceitar criar o WebSocket
        console.error("Erro ao criar WebSocket:", err);
        return;
    }

    // Conectado
    ws.onopen = () => {
        console.log("🟢 Conexão WebSocket estabelecida!");
    };

    // Recebendo mensagens
    ws.onmessage = (event) => {
        if (event.data === "ping") {
            // Responde ao 'ping' enviado pelo servidor
            ws.send("pong");
            return;
        }
        // Exibe o log no contêiner
        logContainer.textContent += event.data + "\n";
        logContainer.scrollTop = logContainer.scrollHeight;
    };

    // Se ocorrer erro de rede, SSL, handshake etc.
    ws.onerror = (errorEvent) => {
        // A depender de sua necessidade, você pode:
        // 1) Logar como 'info' ou 'warn' (em vez de 'error'),
        // 2) Ocultar completamente,
        // 3) Exibir mensagem amigável ao usuário.
        console.warn("🔴 Erro (WebSocket) - mas ignorando detalhes:", errorEvent);
    };

    // Quando fechar, tenta reconectar
    ws.onclose = (closeEvent) => {
        console.warn("🟡 Conexão WebSocket encerrada.", closeEvent.reason || "");
        setTimeout(() => {
            //console.log("Tentando reconectar...");
            connectWebSocket();
        }, 5000);
    };
}

// Executa no carregamento
connectWebSocket();