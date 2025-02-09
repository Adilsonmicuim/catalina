import os
import asyncio
import subprocess
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

# Caminho do log do Tomcat
LOG_PATH = "/opt/tomcat/logs/catalina.out"

# Servindo arquivos estáticos
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
async def serve_index():
    return FileResponse("static/index.html")


# Função para transmitir logs
async def stream_logs(websocket: WebSocket):
    try:
        await websocket.accept()
        print("✅ WebSocket conectado:", websocket.client)

        if not os.path.exists(LOG_PATH):
            await websocket.send_text("[ERRO] Arquivo de log não encontrado.")
            await websocket.close()
            return

        # Inicia o `tail -F` sem buffering
        process = subprocess.Popen(
            ["tail", "-n", "10", "-F", LOG_PATH],  # "-F" garante atualização em tempo real
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # 🔥 Evita buffering do Python
            universal_newlines=True
        )

        try:
            while True:
                line = process.stdout.readline()
                if not line:
                    await asyncio.sleep(0.0)
                    continue

                # 🔄 Evita desconexão automática enviando um "ping"
                if websocket.client_state.name == "CONNECTED":
                    await websocket.send_text(line.strip())
                    await websocket.send_text("ping")  # Mantém a conexão ativa
                else:
                    print("🔌 Cliente desconectado.")
                    break  # Sai do loop se a conexão cair

                await asyncio.sleep(0)


        except WebSocketDisconnect:
            print("❌ Cliente desconectado.")
        except Exception as e:
            print(f"❌ Erro WebSocket: {e}")
        finally:
            process.terminate()
            await websocket.close()
            print("🔌 Conexão WebSocket encerrada.")

    except Exception as e:
        print(f"❌ Erro ao aceitar WebSocket: {e}")


@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    await stream_logs(websocket)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
