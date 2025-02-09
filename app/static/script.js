const logContainer = document.getElementById("log-container");

function connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    let ws = new WebSocket(`${protocol}//${window.location.host}/ws/logs`);

    ws.onopen = () => {
        console.log("✅ Conexão WebSocket estabelecida!");
    };

    ws.onmessage = (event) => {
        if (event.data === "ping") {
            ws.send("pong"); // Responde ao "ping" para manter conexão ativa
            return;
        }

        logContainer.textContent += event.data + "\n";
        logContainer.scrollTop = logContainer.scrollHeight;
    };

    ws.onerror = (error) => {
        console.error("❌ Erro no WebSocket:", error);
    };

    ws.onclose = () => {
        console.warn("🔌 Conexão WebSocket encerrada. Tentando reconectar...");
        setTimeout(connectWebSocket, 5000);
    };
}

connectWebSocket();