        // Definir o logContainer
        const logContainer = document.getElementById("log-container");

        // Verifica o protocolo da página (HTTPS ou HTTP)
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";

        // Cria a conexão WebSocket com segurança (WSS para HTTPS)
        let ws = new WebSocket(`${protocol}//${window.location.host}/ws/logs`);

        // Quando a conexão for aberta com sucesso
        ws.onopen = () => {
            console.log("✅ Conexão WebSocket estabelecida!");
        };

        // Recebe e exibe as mensagens do servidor
        ws.onmessage = (event) => {
            if (event.data.startsWith("[ERRO]")) {
                logContainer.innerHTML = `<span style="color: red; font-weight: bold;">${event.data}</span>`;
                ws.close(); // Fecha a conexão WebSocket em caso de erro
            } else {
                logContainer.textContent += event.data + "\n";
                logContainer.scrollTop = logContainer.scrollHeight; // Scroll automático para o final
            }
        };

        // Lida com erros na conexão WebSocket
        ws.onerror = (error) => {
            console.error("❌ Erro no WebSocket:", error);
        };

        // Reconecta automaticamente caso o WebSocket seja fechado
        ws.onclose = (event) => {
            console.warn("🔌 Conexão WebSocket encerrada. Tentando reconectar...");
            setTimeout(() => {
                ws = new WebSocket(`${protocol}//${window.location.host}/ws/logs`);
            }, 10000); // Tenta reconectar após 10 segundos
        };
